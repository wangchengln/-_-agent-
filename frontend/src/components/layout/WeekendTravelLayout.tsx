"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { MapPin, MessageSquare } from "lucide-react";
import ChatPanel from "@/components/chat/ChatPanel";
import RecommendFeed from "@/components/recommend/RecommendFeed";
import ResizeHandle from "@/components/layout/ResizeHandle";
import { useApp } from "@/lib/store";

const CHAT_WIDTH_STORAGE_KEY = "openclaw-weekend-chat-width";
const DEFAULT_CHAT_WIDTH = 42;
const MIN_CHAT_WIDTH = 28;
const MAX_CHAT_WIDTH = 58;

type MobileTab = "chat" | "recommend";

interface Props {
  onOpenRaw: () => void;
  onOpenCanvas: () => void;
  onOpenPreference: () => void;
  onOpenItinerary: () => void;
}

function readStoredChatWidth(): number {
  if (typeof window === "undefined") return DEFAULT_CHAT_WIDTH;
  try {
    const stored = localStorage.getItem(CHAT_WIDTH_STORAGE_KEY);
    if (!stored) return DEFAULT_CHAT_WIDTH;
    const value = Number(stored);
    if (!Number.isFinite(value)) return DEFAULT_CHAT_WIDTH;
    return Math.min(MAX_CHAT_WIDTH, Math.max(MIN_CHAT_WIDTH, value));
  } catch {
    return DEFAULT_CHAT_WIDTH;
  }
}

export default function WeekendTravelLayout({
  onOpenRaw,
  onOpenCanvas,
  onOpenPreference,
  onOpenItinerary,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [chatWidthPct, setChatWidthPct] = useState(DEFAULT_CHAT_WIDTH);
  const [mobileTab, setMobileTab] = useState<MobileTab>("recommend");
  const { chatFocusNonce } = useApp();

  useEffect(() => {
    if (chatFocusNonce > 0) {
      setMobileTab("chat");
    }
  }, [chatFocusNonce]);

  useEffect(() => {
    setChatWidthPct(readStoredChatWidth());
  }, []);

  const persistChatWidth = useCallback((value: number) => {
    const clamped = Math.min(MAX_CHAT_WIDTH, Math.max(MIN_CHAT_WIDTH, value));
    setChatWidthPct(clamped);
    try {
      localStorage.setItem(CHAT_WIDTH_STORAGE_KEY, String(clamped));
    } catch {
      // ignore
    }
  }, []);

  const handleResize = useCallback(
    (deltaPx: number) => {
      const container = containerRef.current;
      if (!container) return;
      const width = container.getBoundingClientRect().width;
      if (width <= 0) return;
      const deltaPct = (deltaPx / width) * 100;
      persistChatWidth(chatWidthPct + deltaPct);
    },
    [chatWidthPct, persistChatWidth]
  );

  const tabButtonClass = (active: boolean) =>
    `flex-1 flex items-center justify-center gap-1.5 py-2.5 text-[12px] font-medium transition-all ${
      active ? "shadow-sm" : "opacity-70 hover:opacity-90"
    }`;

  return (
    <div className="flex flex-col h-full min-w-0">
      {/* Mobile scene tabs — same panels, one visible at a time */}
      <div
        className="lg:hidden flex shrink-0 px-2 pt-2 pb-0 gap-1"
        role="tablist"
        aria-label="周末出行面板"
      >
        <button
          type="button"
          role="tab"
          aria-selected={mobileTab === "chat"}
          onClick={() => setMobileTab("chat")}
          className={tabButtonClass(mobileTab === "chat")}
          style={
            mobileTab === "chat"
              ? {
                  background: "var(--bg-surface)",
                  color: "var(--accent)",
                  borderRadius: "8px 8px 0 0",
                  border: "1px solid var(--border)",
                  borderBottom: "none",
                }
              : { color: "var(--text-muted)" }
          }
        >
          <MessageSquare className="w-3.5 h-3.5" />
          对话
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mobileTab === "recommend"}
          onClick={() => setMobileTab("recommend")}
          className={tabButtonClass(mobileTab === "recommend")}
          style={
            mobileTab === "recommend"
              ? {
                  background: "var(--bg-surface)",
                  color: "var(--accent)",
                  borderRadius: "8px 8px 0 0",
                  border: "1px solid var(--border)",
                  borderBottom: "none",
                }
              : { color: "var(--text-muted)" }
          }
        >
          <MapPin className="w-3.5 h-3.5" />
          推荐
        </button>
      </div>

      {/* Desktop: resizable dual column */}
      <div
        ref={containerRef}
        className="hidden lg:flex flex-1 min-h-0 overflow-hidden"
      >
        <div
          className="shrink-0 flex flex-col min-h-0 overflow-hidden"
          style={{
            width: `${chatWidthPct}%`,
            minWidth: 280,
            borderRight: "1px solid var(--border)",
          }}
        >
          <ChatPanel
            embedded
            onOpenRaw={onOpenRaw}
            onOpenCanvas={onOpenCanvas}
          />
        </div>
        <ResizeHandle onResize={handleResize} direction="left" />
        <div className="flex-1 min-w-[320px] min-h-0 overflow-hidden">
          <RecommendFeed
            embedded
            onOpenPreference={onOpenPreference}
            onOpenItinerary={onOpenItinerary}
          />
        </div>
      </div>

      {/* Mobile: single active panel */}
      <div className="lg:hidden flex-1 min-h-0 overflow-hidden">
        {mobileTab === "chat" ? (
          <ChatPanel
            embedded
            onOpenRaw={onOpenRaw}
            onOpenCanvas={onOpenCanvas}
          />
        ) : (
          <RecommendFeed
            embedded
            onOpenPreference={onOpenPreference}
            onOpenItinerary={onOpenItinerary}
          />
        )}
      </div>
    </div>
  );
}
