"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  Plus,
  MoreHorizontal,
  Pencil,
  Trash2,
  Check,
  X,
  Brain,
  Zap,
  BookOpen,
  Lightbulb,
  FileText,
  Layers,
  ChevronDown,
  PanelLeftClose,
} from "lucide-react";
import { useApp } from "@/lib/store";
import { listSkills } from "@/lib/api";
import ConfirmDialog from "@/components/shared/ConfirmDialog";

const NAV_ITEMS = [
  { label: "对话", sub: "Chat", icon: MessageSquare, href: "/" },
  { label: "技能管理", sub: "Agent Skills", icon: Zap, href: "/skills" },
  { label: "记忆系统", sub: "Memory System", icon: Brain, href: "/memory" },
];

// Shared skill enabled state across sidebar and skill library
// This is a simple module-level store; in a real app you'd use context or zustand
let _skillEnabledMap: Record<string, boolean> = {};
let _listeners: Array<() => void> = [];

export function getSkillEnabledMap() { return _skillEnabledMap; }
export function setSkillEnabled(name: string, enabled: boolean) {
  _skillEnabledMap = { ..._skillEnabledMap, [name]: enabled };
  _listeners.forEach((fn) => fn());
}
export function initSkillEnabledMap(map: Record<string, boolean>) {
  _skillEnabledMap = { ..._skillEnabledMap, ...map };
  _listeners.forEach((fn) => fn());
}
function useSkillEnabledMap() {
  const [, setTick] = useState(0);
  useEffect(() => {
    const fn = () => setTick((t) => t + 1);
    _listeners.push(fn);
    return () => { _listeners = _listeners.filter((l) => l !== fn); };
  }, []);
  return _skillEnabledMap;
}

export default function Sidebar() {
  const pathname = usePathname();
  const {
    sessionId,
    setSessionId,
    sessions,
    createSession,
    renameSession,
    deleteSession,
    toggleSidebar,
  } = useApp();

  const [skills, setSkills] = useState<Array<{ name: string; description: string }>>([]);
  const enabledMap = useSkillEnabledMap();

  useEffect(() => {
    listSkills()
      .then((list) => {
        setSkills(list);
        const map: Record<string, boolean> = {};
        list.forEach((s) => { map[s.name] = true; });
        initSkillEnabledMap(map);
      })
      .catch(() => setSkills([]));
  }, []);

  const isChat = pathname === "/";
  const isMemoryOrSkills = pathname === "/memory" || pathname === "/skills";

  return (
    <aside className="flex flex-col h-full w-64 shrink-0" style={{ background: "var(--bg-sidebar)", borderRight: "1px solid var(--border)" }}>
      {/* Collapse button */}
      <div className="flex items-center justify-end px-3 pt-2 pb-0">
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-lg transition-colors hover:opacity-80"
          style={{ color: "var(--text-muted)" }}
          title="收起侧边栏"
        >
          <PanelLeftClose className="w-4 h-4" />
        </button>
      </div>

      {/* Navigation */}
      <div className="p-4 pb-2 pt-1">
        <div className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg transition-all ${
                  active
                    ? "font-bold shadow-sm"
                    : "hover:opacity-80"
                }`}
                style={
                  active
                    ? { background: "var(--bg-surface)", color: "var(--accent)" }
                    : { color: "var(--text-secondary)" }
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <div className="flex items-baseline gap-1.5">
                  <span className="text-[13px]">{item.label}</span>
                  <span className="text-[10px] font-normal" style={{ color: active ? "var(--accent)" : "var(--text-muted)", opacity: 0.7 }}>{item.sub}</span>
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      <div className="mx-4 h-px" style={{ background: "var(--border)" }} />

      {/* Context-dependent content below navigation */}
      {isChat ? (
        /* Chat page: Session list */
        <>
          <div className="p-2 pb-0">
            <button
              onClick={createSession}
              className="w-full flex items-center gap-2 px-3 py-2 text-[13px] font-medium rounded-lg transition-all hover:opacity-80"
              style={{ color: "var(--accent)" }}
            >
              <Plus className="w-4 h-4" />
              New Chat
            </button>
          </div>
          <div className="flex-1 overflow-y-auto px-1.5 mt-1">
            {sessions.length > 0 && (
              <div className="space-y-0.5">
                <p className="px-3 pt-1 pb-1 text-[10px] font-semibold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                  Recent
                </p>
                {sessions.map((s) => (
                  <SessionItem
                    key={s.id}
                    id={s.id}
                    title={s.title}
                    irfSummary={s.irf_summary}
                    irfRound={s.irf_round}
                    isActive={sessionId === s.id}
                    onSelect={() => setSessionId(s.id)}
                    onRename={(title) => renameSession(s.id, title)}
                    onDelete={() => deleteSession(s.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </>
      ) : pathname === "/skills" ? (
        /* Skills page: collapsible description + enabled skills */
        <>
          <div className="flex-1 overflow-y-auto p-4 pt-2">
            {/* Skills intro — collapsible */}
            <CollapsibleInfo
              icon={<BookOpen className="w-4 h-4" style={{ color: "var(--accent)" }} />}
              title="什么是 Agent Skills?"
            >
              <p className="text-[11px] leading-relaxed mb-3" style={{ color: "var(--text-secondary)" }}>
                技能是 Agent 的能力扩展模块。每个技能由一个 Markdown 文件定义，包含触发条件、执行步骤和示例。
              </p>
              <div className="space-y-3">
                <div className="flex gap-2.5">
                  <Lightbulb className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "var(--accent)" }} />
                  <div>
                    <p className="text-[11px] font-semibold mb-0.5" style={{ color: "var(--text-primary)" }}>指令驱动</p>
                    <p className="text-[10px] leading-relaxed" style={{ color: "var(--text-muted)" }}>
                      不同于传统 Function Calling，技能通过自然语言指令定义，Agent 阅读后自主执行。
                    </p>
                  </div>
                </div>
                <div className="flex gap-2.5">
                  <FileText className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "var(--accent)" }} />
                  <div>
                    <p className="text-[11px] font-semibold mb-0.5" style={{ color: "var(--text-primary)" }}>SKILL.md 规范</p>
                    <p className="text-[10px] leading-relaxed" style={{ color: "var(--text-muted)" }}>
                      遵循 agentskills.io 开放标准，YAML frontmatter 定义元数据，正文编写详细操作指令。
                    </p>
                  </div>
                </div>
                <div className="flex gap-2.5">
                  <Layers className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "var(--accent)" }} />
                  <div>
                    <p className="text-[11px] font-semibold mb-0.5" style={{ color: "var(--text-primary)" }}>组合使用</p>
                    <p className="text-[10px] leading-relaxed" style={{ color: "var(--text-muted)" }}>
                      Agent 可以在一次对话中组合多个技能，配合 Core Tools 完成复杂任务。
                    </p>
                  </div>
                </div>
              </div>
            </CollapsibleInfo>
          </div>

          {/* Enabled skills — pinned at bottom */}
          <div className="shrink-0 p-4 pt-2" style={{ borderTop: "1px solid var(--border)" }}>
            <p className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: "var(--text-muted)" }}>
              已启用技能
            </p>
            <div className="space-y-1.5">
              {skills.length === 0 ? (
                <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>暂无技能</p>
              ) : (
                skills.map((s) => {
                  const isEnabled = enabledMap[s.name] !== false;
                  return (
                    <div key={s.name} className="flex items-center gap-2 text-[12px]">
                      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isEnabled ? "bg-green-500" : "bg-gray-400"}`} />
                      <span style={{ color: isEnabled ? "var(--text-secondary)" : "var(--text-muted)" }}>{s.name}</span>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </>
      ) : pathname === "/memory" ? (
        /* Memory page: collapsible description + core files pinned at bottom */
        <>
          <div className="flex-1 overflow-y-auto p-4 pt-2">
            {/* Memory intro — collapsible */}
            <CollapsibleInfo
              icon={<Brain className="w-4 h-4" style={{ color: "var(--accent)" }} />}
              title="什么是 Memory System?"
            >
              <p className="text-[11px] leading-relaxed mb-3" style={{ color: "var(--text-secondary)" }}>
                记忆系统是 Agent 的长期知识存储。通过 Markdown 文件管理 Agent 的身份、行为规则和用户偏好。
              </p>
              <div className="space-y-3">
                <div className="flex gap-2.5">
                  <FileText className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "var(--accent)" }} />
                  <div>
                    <p className="text-[11px] font-semibold mb-0.5" style={{ color: "var(--text-primary)" }}>文件即记忆</p>
                    <p className="text-[10px] leading-relaxed" style={{ color: "var(--text-muted)" }}>
                      不同于向量数据库，所有记忆都以可读的 Markdown 文件存储，完全透明可编辑。
                    </p>
                  </div>
                </div>
                <div className="flex gap-2.5">
                  <Layers className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "var(--accent)" }} />
                  <div>
                    <p className="text-[11px] font-semibold mb-0.5" style={{ color: "var(--text-primary)" }}>分层架构</p>
                    <p className="text-[10px] leading-relaxed" style={{ color: "var(--text-muted)" }}>
                      SOUL.md 定义人格、IDENTITY.md 定义身份、USER.md 记录用户、MEMORY.md 存储长期记忆。
                    </p>
                  </div>
                </div>
                <div className="flex gap-2.5">
                  <Lightbulb className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "var(--accent)" }} />
                  <div>
                    <p className="text-[11px] font-semibold mb-0.5" style={{ color: "var(--text-primary)" }}>RAG 检索模式</p>
                    <p className="text-[10px] leading-relaxed" style={{ color: "var(--text-muted)" }}>
                      当 MEMORY.md 过长时，可开启 RAG 模式，系统自动检索相关记忆片段注入上下文。
                    </p>
                  </div>
                </div>
              </div>
            </CollapsibleInfo>
          </div>

          {/* Core files — pinned at bottom */}
          <div className="shrink-0 p-4 pt-2" style={{ borderTop: "1px solid var(--border)" }}>
            <p className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: "var(--text-muted)" }}>
              核心文件
            </p>
            <div className="space-y-1.5">
              {[
                { name: "SOUL.md", desc: "人格与边界" },
                { name: "IDENTITY.md", desc: "身份与风格" },
                { name: "USER.md", desc: "用户画像" },
                { name: "AGENTS.md", desc: "操作指南" },
                { name: "MEMORY.md", desc: "长期记忆" },
              ].map((f) => (
                <div key={f.name} className="flex items-center justify-between text-[11px]">
                  <span className="font-mono" style={{ color: "var(--text-secondary)" }}>{f.name}</span>
                  <span style={{ color: "var(--text-muted)" }}>{f.desc}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : (
        <div className="flex-1" />
      )}
    </aside>
  );
}

// ── Collapsible Info ────────────────────────────────────

function CollapsibleInfo({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-lg mb-3 overflow-hidden" style={{ background: "var(--accent-bg)", border: "1px solid var(--border)" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between p-3 text-left transition-colors hover:opacity-90"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-[12px] font-semibold" style={{ color: "var(--accent)" }}>{title}</span>
        </div>
        <ChevronDown
          className="w-3.5 h-3.5 transition-transform"
          style={{ color: "var(--accent)", transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
        />
      </button>
      {open && (
        <div className="px-3 pb-3 animate-fade-in">
          {children}
        </div>
      )}
    </div>
  );
}

// ── Session Item ────────────────────────────────────────

function SessionItem({
  id,
  title,
  irfSummary,
  irfRound,
  isActive,
  onSelect,
  onRename,
  onDelete,
}: {
  id: string;
  title: string;
  irfSummary?: string | null;
  irfRound?: number | null;
  isActive: boolean;
  onSelect: () => void;
  onRename: (title: string) => void;
  onDelete: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState(title);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  useEffect(() => {
    if (renaming && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [renaming]);

  const handleRenameSubmit = useCallback(() => {
    const trimmed = renameValue.trim();
    if (trimmed && trimmed !== title) {
      onRename(trimmed);
    }
    setRenaming(false);
  }, [renameValue, title, onRename]);

  const handleDelete = useCallback(() => {
    setMenuOpen(false);
    setShowDeleteConfirm(true);
  }, []);

  if (renaming) {
    return (
      <div className="flex items-center gap-1 px-2 py-1">
        <input
          ref={inputRef}
          className="flex-1 px-2 py-1 text-[13px] rounded-md border outline-none"
          style={{ borderColor: "var(--border-accent)", background: "var(--bg-surface)", color: "var(--text-primary)" }}
          value={renameValue}
          onChange={(e) => setRenameValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleRenameSubmit();
            if (e.key === "Escape") setRenaming(false);
          }}
          onBlur={handleRenameSubmit}
        />
        <button onClick={handleRenameSubmit} className="p-1 text-green-600 hover:bg-green-50 rounded">
          <Check className="w-3.5 h-3.5" />
        </button>
        <button onClick={() => setRenaming(false)} className="p-1 rounded" style={{ color: "var(--text-muted)" }}>
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div className="relative group" ref={menuRef}>
      <button
        onClick={onSelect}
        className={`w-full flex flex-col gap-0.5 px-3 py-2 text-[13px] rounded-lg transition-all text-left relative pr-8 ${
          isActive ? "font-medium shadow-sm" : "hover:opacity-80"
        }`}
        style={
          isActive
            ? { background: "var(--bg-surface)", color: "var(--text-primary)" }
            : { color: "var(--text-secondary)" }
        }
      >
        {isActive && (
          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full" style={{ background: "var(--accent)" }} />
        )}
        <span className="truncate">{title}</span>
        {(irfSummary || (irfRound != null && irfRound > 0)) && (
          <span
            className="text-[10px] truncate leading-snug"
            style={{ color: isActive ? "var(--text-muted)" : "var(--text-muted)", opacity: 0.9 }}
          >
            {irfRound != null && irfRound > 0 ? `第 ${irfRound} 轮` : ""}
            {irfRound != null && irfRound > 0 && irfSummary ? " · " : ""}
            {irfSummary ?? ""}
          </span>
        )}
      </button>

      <div className="absolute right-1 top-1/2 -translate-y-1/2">
        <button
          onClick={(e) => { e.stopPropagation(); setMenuOpen((v) => !v); }}
          className="p-1 rounded-md opacity-0 group-hover:opacity-100 transition-all"
          style={{ color: "var(--text-muted)" }}
        >
          <MoreHorizontal className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Dropdown menu — rendered as fixed position to escape overflow:hidden */}
      {menuOpen && <SessionMenu
        onRename={() => { setMenuOpen(false); setRenameValue(title); setRenaming(true); }}
        onDelete={handleDelete}
        onClose={() => setMenuOpen(false)}
        menuRef={menuRef}
      />}

      {/* Delete confirmation dialog */}
      {showDeleteConfirm && (
        <ConfirmDialog
          title="删除会话"
          message={`确定要删除会话「${title}」吗？此操作不可撤销。`}
          confirmText="删除"
          danger
          onConfirm={() => { setShowDeleteConfirm(false); onDelete(); }}
          onCancel={() => setShowDeleteConfirm(false)}
        />
      )}
    </div>
  );
}

/** Fixed-position dropdown to escape sidebar overflow clipping */
function SessionMenu({
  onRename,
  onDelete,
  onClose,
  menuRef,
}: {
  onRename: () => void;
  onDelete: () => void;
  onClose: () => void;
  menuRef: React.RefObject<HTMLDivElement | null>;
}) {
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  useEffect(() => {
    if (menuRef.current) {
      const rect = menuRef.current.getBoundingClientRect();
      setPos({ top: rect.bottom + 4, left: rect.right - 128 });
    }
  }, [menuRef]);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node) &&
          menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose, menuRef]);

  return (
    <div
      ref={dropdownRef}
      className="fixed w-32 rounded-lg shadow-lg py-1 animate-fade-in-scale"
      style={{
        top: pos.top,
        left: pos.left,
        zIndex: 9999,
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
      }}
    >
      <button
        onClick={onRename}
        className="w-full flex items-center gap-2 px-3 py-1.5 text-[12px] transition-colors hover:opacity-80"
        style={{ color: "var(--text-secondary)" }}
      >
        <Pencil className="w-3 h-3" />
        Rename
      </button>
      <button
        onClick={onDelete}
        className="w-full flex items-center gap-2 px-3 py-1.5 text-[12px] text-red-500 hover:bg-red-50 transition-colors"
      >
        <Trash2 className="w-3 h-3" />
        Delete
      </button>
    </div>
  );
}
