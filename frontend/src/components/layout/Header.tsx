"use client";

import { Sun, Moon, GraduationCap, PanelLeftOpen, MessageSquare, MapPin } from "lucide-react";
import { useTheme } from "@/lib/theme";
import { useApp } from "@/lib/store";

interface Props {
  onToggleLearnMode?: () => void;
  learnModeOpen?: boolean;
}

export default function Header({ onToggleLearnMode, learnModeOpen }: Props) {
  const { theme, setTheme } = useTheme();
  const { sidebarOpen, toggleSidebar, recommendMode, setRecommendMode } = useApp();

  const modeOptions = [
    { enabled: false, label: "对话", icon: MessageSquare, title: "通用对话模式" },
    { enabled: true, label: "推荐", icon: MapPin, title: "周末出行 IRF 推荐模式" },
  ] as const;

  return (
    <header className="glass-nav sticky top-0 z-50 h-14 flex items-center px-4 shrink-0">
      {/* Left — Sidebar toggle (when closed) + Learn Mode */}
      <div className="flex items-center gap-3 w-48 shrink-0">
        {!sidebarOpen && (
          <button
            onClick={toggleSidebar}
            className="p-1.5 rounded-lg transition-colors hover:opacity-80"
            style={{ color: "var(--text-muted)" }}
            title="展开侧边栏"
          >
            <PanelLeftOpen className="w-4 h-4" />
          </button>
        )}
        {onToggleLearnMode && (
          <button
            onClick={onToggleLearnMode}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all"
            style={{
              background: learnModeOpen ? "var(--accent-bg)" : "transparent",
              color: learnModeOpen ? "var(--accent)" : "var(--text-secondary)",
              border: `1px solid ${learnModeOpen ? "var(--accent)" : "var(--border)"}`,
            }}
          >
            <GraduationCap className="w-4 h-4" />
            学习模式
          </button>
        )}
      </div>

      {/* Center — Logo + mode switch */}
      <div className="flex-1 flex items-center justify-center gap-4 min-w-0">
        <div className="flex items-center gap-2.5 shrink-0">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center shadow-sm"
            style={{ background: "linear-gradient(135deg, var(--accent), var(--accent-hover))" }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"
                fill="white"
                fillOpacity="0.15"
                stroke="white"
                strokeWidth="1"
              />
              <path
                d="M8 8.5C8 7.12 8.9 6 10 6s2 1.12 2 2.5V13H8V8.5z"
                fill="white"
                fillOpacity="0.85"
              />
              <path
                d="M14 7.5C14 6.12 14.9 5 16 5s2 1.12 2 2.5V13h-4V7.5z"
                fill="white"
                fillOpacity="0.85"
              />
              <path
                d="M6 10c0-1.1.67-2 1.5-2S9 8.9 9 10v3H6v-3z"
                fill="white"
                fillOpacity="0.7"
              />
              <path
                d="M6 13c0 3.31 2.69 6 6 6s6-2.69 6-6H6z"
                fill="white"
                fillOpacity="0.9"
              />
            </svg>
          </div>
          <span className="text-[15px] tracking-tight font-bold" style={{ color: "var(--text-primary)" }}>
            Mini OpenClaw
          </span>
        </div>

        {/* Chat / Recommend mode toggle */}
        <div
          className="flex items-center rounded-lg p-0.5 shrink-0"
          style={{ background: "var(--accent-bg)", border: "1px solid var(--border)" }}
          role="tablist"
          aria-label="应用模式"
        >
          {modeOptions.map(({ enabled, label, icon: Icon, title }) => {
            const active = recommendMode === enabled;
            return (
              <button
                key={label}
                type="button"
                role="tab"
                aria-selected={active}
                title={title}
                onClick={() => setRecommendMode(enabled)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                  active ? "shadow-sm" : "opacity-60 hover:opacity-90"
                }`}
                style={
                  active
                    ? { background: "var(--bg-surface)", color: "var(--accent)" }
                    : { color: "var(--text-muted)" }
                }
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
              </button>
            );
          })}
        </div>

        {/* <a
          href="https://fufan.ai"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[12px] font-semibold tracking-wide transition-colors hover:opacity-80"
          style={{ color: "var(--accent)" }}
        >
          赋范空间
          <ExternalLink className="w-3 h-3" />
        </a> */}
      </div>

      {/* Right — Theme + Status */}
      <div className="flex items-center gap-4 w-48 shrink-0 justify-end">
        {/* Theme toggle group */}
        <div className="flex items-center rounded-lg p-0.5" style={{ background: "var(--accent-bg)" }}>
          {([
            { key: "dark" as const, icon: Moon, label: "Dark" },
            { key: "light" as const, icon: Sun, label: "Light" },
          ]).map(({ key, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTheme(key)}
              className={`p-1.5 rounded-md transition-all ${
                theme === key
                  ? "shadow-sm"
                  : "opacity-50 hover:opacity-80"
              }`}
              style={theme === key ? { background: "var(--bg-surface)", color: "var(--accent)" } : { color: "var(--text-muted)" }}
              title={key}
            >
              <Icon className="w-3.5 h-3.5" />
            </button>
          ))}
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-1.5 text-[11px]" style={{ color: "var(--text-muted)" }}>
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
          </span>
          System: Online
        </div>
      </div>
    </header>
  );
}
