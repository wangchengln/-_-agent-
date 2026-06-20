"use client";

import { useEffect, useState } from "react";
import { Brain, Sparkles, FileText, Zap, Filter, RefreshCw } from "lucide-react";
import { getFileTokenCounts } from "@/lib/api";

const MEMORY_FILES = [
  { label: "MEMORY.md", path: "memory/MEMORY.md", icon: Brain, description: "跨会话长期记忆存储" },
  { label: "SOUL.md", path: "workspace/SOUL.md", icon: Sparkles, description: "Agent 人格与行为边界" },
  { label: "IDENTITY.md", path: "workspace/IDENTITY.md", icon: FileText, description: "名称、风格、表情设定" },
  { label: "USER.md", path: "workspace/USER.md", icon: FileText, description: "用户画像与偏好" },
  { label: "AGENTS.md", path: "workspace/AGENTS.md", icon: FileText, description: "运行指令与记忆协议" },
  { label: "SKILLS_SNAPSHOT.md", path: "SKILLS_SNAPSHOT.md", icon: Zap, description: "自动生成的技能清单" },
];

interface Props {
  selectedFile: string | null;
  onSelect: (path: string) => void;
}

export default function MemoryFileList({ selectedFile, onSelect }: Props) {
  const [tokenCounts, setTokenCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    const paths = MEMORY_FILES.map((f) => f.path);
    getFileTokenCounts(paths)
      .then((data) => {
        const counts: Record<string, number> = {};
        for (const f of data.files) counts[f.path] = f.tokens;
        setTokenCounts(counts);
      })
      .catch(() => {});
  }, []);

  const refreshTokens = () => {
    const paths = MEMORY_FILES.map((f) => f.path);
    getFileTokenCounts(paths)
      .then((data) => {
        const counts: Record<string, number> = {};
        for (const f of data.files) counts[f.path] = f.tokens;
        setTokenCounts(counts);
      })
      .catch(() => {});
  };

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-[14px] font-semibold" style={{ color: "var(--text-primary)" }}>
          核心记忆文件
        </h2>
        <div className="flex items-center gap-1">
          <button className="p-1.5 rounded-md transition-colors hover:opacity-80" style={{ color: "var(--text-muted)" }}>
            <Filter className="w-3.5 h-3.5" />
          </button>
          <button onClick={refreshTokens} className="p-1.5 rounded-md transition-colors hover:opacity-80" style={{ color: "var(--text-muted)" }}>
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* File cards */}
      <div className="space-y-3">
        {MEMORY_FILES.map((file) => {
          const Icon = file.icon;
          const isSelected = selectedFile === file.path;
          const tokens = tokenCounts[file.path];

          return (
            <button
              key={file.path}
              onClick={() => onSelect(file.path)}
              className={`w-full text-left p-4 rounded-xl transition-all ${
                isSelected ? "shadow-md ring-1" : "shadow-sm hover:shadow-md"
              }`}
              style={{
                background: "var(--bg-surface)",
                border: `1px solid ${isSelected ? "var(--accent)" : "var(--border)"}`,
                ...(isSelected ? { ringColor: "var(--accent)" } : {}),
              }}
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: "var(--accent-bg)" }}>
                  <Icon className="w-4 h-4" style={{ color: "var(--accent)" }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[13px] font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                      {file.label}
                    </span>
                    {tokens !== undefined && tokens > 0 && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full shrink-0" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
                        {tokens}t
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] mt-0.5 truncate" style={{ color: "var(--text-muted)" }}>
                    {file.description}
                  </p>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
