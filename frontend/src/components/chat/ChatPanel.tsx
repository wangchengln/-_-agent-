"use client";

import { useEffect, useRef, useState } from "react";
import { useApp } from "@/lib/store";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import SettingsModal from "@/components/shared/SettingsModal";
import { Sparkles, FileCode, MonitorPlay, Settings } from "lucide-react";

interface Props {
  onOpenRaw: () => void;
  onOpenCanvas: () => void;
  /** Compact header when embedded in weekend dual-column layout */
  embedded?: boolean;
}

export default function ChatPanel({ onOpenRaw, onOpenCanvas, embedded = false }: Props) {
  const { messages, sessions, sessionId } = useApp();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const currentTitle = sessions.find((s) => s.id === sessionId)?.title || sessionId;

  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div
        className={`${embedded ? "h-12 px-4" : "h-14 px-6"} flex items-center justify-between shrink-0`}
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-2 min-w-0">
          {embedded && (
            <span
              className="text-[10px] font-semibold uppercase tracking-wider shrink-0 px-1.5 py-0.5 rounded"
              style={{ background: "var(--accent-bg)", color: "var(--accent)" }}
            >
              对话
            </span>
          )}
          <span
            className={`${embedded ? "text-[13px]" : "text-[14px]"} font-semibold truncate`}
            style={{ color: "var(--text-primary)" }}
          >
            {currentTitle}
          </span>
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onOpenCanvas}
            className="p-2 rounded-lg transition-colors hover:opacity-80"
            style={{ color: "var(--text-muted)" }}
            title="Canvas Preview"
          >
            <MonitorPlay className="w-4 h-4" />
          </button>
          <button
            onClick={onOpenRaw}
            className="p-2 rounded-lg transition-colors hover:opacity-80"
            style={{ color: "var(--text-muted)" }}
            title="Raw Messages"
          >
            <FileCode className="w-4 h-4" />
          </button>
          <button
            onClick={() => setSettingsOpen(true)}
            className="p-2 rounded-lg transition-colors hover:opacity-80"
            style={{ color: "var(--text-muted)" }}
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4 shadow-lg" style={{ background: "var(--accent)" }}>
              <Sparkles className="w-7 h-7 text-white" />
            </div>
            <h2 className="text-lg font-semibold mb-1" style={{ color: "var(--text-primary)" }}>
              Hi, how can I help?
            </h2>
            <p className="text-[13px] max-w-xs text-center leading-relaxed" style={{ color: "var(--text-muted)" }}>
              {embedded
                ? "和我聊聊出行想法，右侧会同步更新推荐"
                : "Ask me anything, or try "}
              {!embedded && (
                <span className="font-medium" style={{ color: "var(--accent)" }}>
                  &quot;查询北京天气&quot;
                </span>
              )}
            </p>
            <div className="flex flex-wrap gap-2 mt-5 max-w-md justify-center">
              {(embedded
                ? ["帮我规划上海周末", "今天适合室外活动吗？", "解释一下当前推荐"]
                : ["你好，介绍一下自己", "查询北京天气", "帮我写一段Python代码"]
              ).map((hint) => (
                <QuickHint key={hint} text={hint} />
              ))}
            </div>
          </div>
        ) : (
          <div className="py-4 px-6 space-y-6">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <ChatInput />

      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}
    </div>
  );
}

function QuickHint({ text }: { text: string }) {
  const { sendMessage, isStreaming, isCompressing } = useApp();
  const disabled = isStreaming || isCompressing;
  return (
    <button
      onClick={() => !disabled && sendMessage(text)}
      disabled={disabled}
      className="px-3 py-1.5 rounded-full text-[12px] transition-all shadow-sm hover:shadow-md disabled:opacity-50"
      style={{ color: "var(--text-secondary)", background: "var(--bg-surface)", border: "1px solid var(--border)" }}
    >
      {text}
    </button>
  );
}
