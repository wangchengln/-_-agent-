"use client";

import { useEffect, useState } from "react";
import { Filter, RefreshCw, Search, Zap, Trash2, Plus, Globe } from "lucide-react";
import { listSkills, deleteSkill } from "@/lib/api";
import ConfirmDialog from "@/components/shared/ConfirmDialog";
import { setSkillEnabled, getSkillEnabledMap, initSkillEnabledMap } from "@/components/layout/Sidebar";
import NewSkillModal from "./NewSkillModal";
import SkillStore from "./SkillStore";

interface SkillInfo {
  name: string;
  path: string;
  description: string;
}

interface Props {
  selectedSkill: string | null;
  onSelect: (skill: { name: string; path: string }) => void;
}

export default function SkillLibrary({ selectedSkill, onSelect }: Props) {
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [search, setSearch] = useState("");
  const [enabledMap, setEnabledMapLocal] = useState<Record<string, boolean>>({});
  const [showNewModal, setShowNewModal] = useState(false);
  const [showStore, setShowStore] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const loadSkills = () => {
    listSkills()
      .then((list) => {
        setSkills(list);
        const currentMap = getSkillEnabledMap();
        const map: Record<string, boolean> = {};
        list.forEach((s) => { map[s.name] = currentMap[s.name] !== undefined ? currentMap[s.name] : true; });
        initSkillEnabledMap(map);
        setEnabledMapLocal(map);
      })
      .catch(() => setSkills([]));
  };

  useEffect(() => { loadSkills(); }, []);

  const handleToggle = (name: string) => {
    const newVal = !(enabledMap[name] ?? true);
    setEnabledMapLocal((prev) => ({ ...prev, [name]: newVal }));
    setSkillEnabled(name, newVal);
  };

  const filtered = skills.filter((s) =>
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.description.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-[14px] font-semibold" style={{ color: "var(--text-primary)" }}>
          技能库
        </h2>
        <div className="flex items-center gap-1">
          <button className="p-1.5 rounded-md transition-colors hover:opacity-80" style={{ color: "var(--text-muted)" }}>
            <Filter className="w-3.5 h-3.5" />
          </button>
          <button onClick={loadSkills} className="p-1.5 rounded-md transition-colors hover:opacity-80" style={{ color: "var(--text-muted)" }}>
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5" style={{ color: "var(--text-muted)" }} />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜索技能..."
          className="w-full pl-9 pr-3 py-2 rounded-lg text-[12px] outline-none transition-all"
          style={{
            background: "var(--bg-page)",
            border: "1px solid var(--border)",
            color: "var(--text-primary)",
          }}
        />
      </div>

      {/* Skill cards */}
      <div className="space-y-4">
        {filtered.map((skill) => {
          const isSelected = selectedSkill === skill.name;
          const isEnabled = enabledMap[skill.name] ?? true;
          const skillDir = skill.path.replace(/\/SKILL\.md$/, "").split("/").pop() || skill.name;

          return (
            <div
              key={skill.name}
              onClick={() => onSelect({ name: skill.name, path: skill.path })}
              className={`rounded-xl p-4 cursor-pointer transition-all ${isSelected ? "shadow-md" : "shadow-sm hover:shadow-md"}`}
              style={{
                border: `1px solid ${isSelected ? "var(--accent)" : "var(--border)"}`,
                background: "var(--bg-surface)",
              }}
            >
              {/* Header */}
              <div className="flex items-center gap-3 mb-2">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ background: "var(--accent-bg)" }}>
                  <Zap className="w-4 h-4" style={{ color: "var(--accent)" }} />
                </div>
                <div className="flex-1 min-w-0">
                  <span className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>{skill.name}</span>
                </div>
                {/* Toggle */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleToggle(skill.name);
                  }}
                  className={`relative w-9 h-5 rounded-full transition-colors ${isEnabled ? "" : "opacity-50"}`}
                  style={{ background: isEnabled ? "var(--accent)" : "var(--border)" }}
                >
                  <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${isEnabled ? "left-[18px]" : "left-0.5"}`} />
                </button>
                {/* Delete */}
                <button
                  onClick={(e) => { e.stopPropagation(); setDeleteTarget(skill.name); }}
                  className="p-1 rounded-md transition-colors hover:bg-red-50"
                  style={{ color: "var(--text-muted)" }}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
              {/* Description */}
              {skill.description && (
                <p className="text-[11px] leading-relaxed mb-2" style={{ color: "var(--text-muted)" }}>
                  {skill.description}
                </p>
              )}
              {/* Footer */}
              <div className="flex items-center gap-2 text-[10px]" style={{ color: "var(--text-muted)" }}>
                <span className="font-mono">skills/{skillDir}/SKILL.md</span>
                <span className="px-1.5 py-0.5 rounded-full" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>v1.0.0</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Action buttons */}
      <div className="mt-4 space-y-2">
        <button
          onClick={() => setShowNewModal(true)}
          className="w-full py-3 rounded-xl text-[13px] font-medium transition-all flex items-center justify-center gap-2"
          style={{ border: "2px dashed var(--border)", color: "var(--text-muted)" }}
        >
          <Plus className="w-4 h-4" />
          创建新的技能
        </button>
        <button
          onClick={() => setShowStore(true)}
          className="w-full py-3 rounded-xl text-[13px] font-medium transition-all flex items-center justify-center gap-2"
          style={{ border: "1px solid var(--accent)", color: "var(--accent)", background: "var(--accent-bg)" }}
        >
          <Globe className="w-4 h-4" />
          技能商店
        </button>
      </div>

      {showNewModal && (
        <NewSkillModal
          onClose={() => setShowNewModal(false)}
          onCreated={() => {
            setShowNewModal(false);
            loadSkills();
          }}
        />
      )}

      {showStore && (
        <SkillStore
          onClose={() => setShowStore(false)}
          onInstalled={() => {
            setShowStore(false);
            loadSkills();
          }}
        />
      )}

      {deleteTarget && (
        <ConfirmDialog
          title="删除技能"
          message={`确定要删除技能「${deleteTarget}」吗？整个技能文件夹将被移除，此操作不可撤销。`}
          confirmText="删除"
          danger
          onConfirm={async () => {
            const name = deleteTarget;
            setDeleteTarget(null);
            try {
              await deleteSkill(name);
              loadSkills();
            } catch {
              // silent
            }
          }}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
