"use client";

import { useState, useEffect, useRef } from "react";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";
import LearnPanel from "@/components/layout/LearnPanel";
import ChatPanel from "@/components/chat/ChatPanel";
import RawMessagesPanel from "@/components/chat/RawMessagesPanel";
import CanvasPanel from "@/components/chat/CanvasPanel";
import { useApp } from "@/lib/store";

type RightPanel = "none" | "raw" | "canvas";

export default function Home() {
  const [rightPanel, setRightPanel] = useState<RightPanel>("none");
  const [learnOpen, setLearnOpen] = useState(false);
  const { canvasStreaming, sessionId, resetCanvas, sidebarOpen } = useApp();
  const wasStreamingRef = useRef(false);
  const prevSessionRef = useRef(sessionId);

  // Auto-open canvas panel when canvas streaming begins
  useEffect(() => {
    if (canvasStreaming && !wasStreamingRef.current) {
      setRightPanel("canvas");
    }
    wasStreamingRef.current = canvasStreaming;
  }, [canvasStreaming]);

  // Close canvas + restore canvas when session changes
  useEffect(() => {
    if (sessionId !== prevSessionRef.current) {
      // Close canvas panel and reset canvas state on session switch
      if (rightPanel === "canvas") {
        setRightPanel("none");
      }
      resetCanvas();
      prevSessionRef.current = sessionId;
    }
  }, [sessionId, rightPanel, resetCanvas]);

  return (
    <div className="h-screen flex flex-col" style={{ background: "var(--bg-page)" }}>
      <Header
        onToggleLearnMode={() => setLearnOpen((v) => !v)}
        learnModeOpen={learnOpen}
      />
      <div className="flex-1 flex overflow-hidden">
        {learnOpen && (
          <LearnPanel onClose={() => setLearnOpen(false)} />
        )}
        <div className={`shrink-0 overflow-hidden transition-all duration-300 ${sidebarOpen ? "w-64" : "w-0"}`}>
          <Sidebar />
        </div>
        <div className="flex-1 overflow-hidden transition-all duration-300">
          <ChatPanel
            onOpenRaw={() => setRightPanel((p) => (p === "raw" ? "none" : "raw"))}
            onOpenCanvas={() => setRightPanel((p) => (p === "canvas" ? "none" : "canvas"))}
          />
        </div>
        {rightPanel === "raw" && (
          <div
            className="w-[520px] shrink-0 overflow-hidden animate-slide-in-right"
            style={{ borderLeft: "1px solid var(--border)" }}
          >
            <RawMessagesPanel onClose={() => setRightPanel("none")} />
          </div>
        )}
        {rightPanel === "canvas" && (
          <div
            className="w-[520px] shrink-0 overflow-hidden animate-slide-in-right"
            style={{ borderLeft: "1px solid var(--border)" }}
          >
            <CanvasPanel onClose={() => setRightPanel("none")} />
          </div>
        )}
      </div>
    </div>
  );
}
