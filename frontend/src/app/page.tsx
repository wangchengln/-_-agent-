"use client";

import { useState, useEffect, useRef } from "react";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";
import LearnPanel from "@/components/layout/LearnPanel";
import ChatPanel from "@/components/chat/ChatPanel";
import WeekendTravelLayout from "@/components/layout/WeekendTravelLayout";
import PreferenceSidebar from "@/components/recommend/PreferenceSidebar";
import ItineraryPanel from "@/components/recommend/ItineraryPanel";
import RawMessagesPanel from "@/components/chat/RawMessagesPanel";
import CanvasPanel from "@/components/chat/CanvasPanel";
import ToastStack from "@/components/shared/ToastStack";
import { useApp } from "@/lib/store";

type RightPanel = "none" | "raw" | "canvas" | "preference" | "itinerary";

export default function Home() {
  const [rightPanel, setRightPanel] = useState<RightPanel>("none");
  const [learnOpen, setLearnOpen] = useState(false);
  const {
    canvasStreaming,
    canvasReady,
    sessionId,
    resetCanvas,
    sidebarOpen,
    recommendMode,
    currentItinerary,
    itineraryCanvasToken,
  } = useApp();
  const wasStreamingRef = useRef(false);
  const prevSessionRef = useRef(sessionId);
  const prevItineraryRef = useRef<typeof currentItinerary>(null);
  const prevCanvasTokenRef = useRef(0);

  // Auto-open canvas panel when canvas streaming begins
  useEffect(() => {
    if (canvasStreaming && !wasStreamingRef.current) {
      setRightPanel("canvas");
    }
    wasStreamingRef.current = canvasStreaming;
  }, [canvasStreaming]);

  // Auto-open canvas when itinerary timeline HTML is generated
  useEffect(() => {
    if (
      itineraryCanvasToken > 0 &&
      itineraryCanvasToken !== prevCanvasTokenRef.current &&
      canvasReady &&
      !canvasStreaming &&
      recommendMode
    ) {
      setRightPanel("canvas");
    }
    prevCanvasTokenRef.current = itineraryCanvasToken;
  }, [itineraryCanvasToken, canvasReady, canvasStreaming, recommendMode]);

  // Auto-open itinerary panel when a new plan is generated (weekend scene)
  useEffect(() => {
    if (currentItinerary && !prevItineraryRef.current && recommendMode) {
      setRightPanel("itinerary");
    }
    if (!currentItinerary && prevItineraryRef.current && rightPanel === "itinerary") {
      setRightPanel("none");
    }
    prevItineraryRef.current = currentItinerary;
  }, [currentItinerary, recommendMode, rightPanel]);

  // Close auxiliary panels and reset canvas when session changes
  useEffect(() => {
    if (sessionId !== prevSessionRef.current) {
      if (rightPanel !== "none") {
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
        <div className="flex-1 overflow-hidden transition-all duration-300 min-w-0">
          {recommendMode ? (
            <WeekendTravelLayout
              onOpenPreference={() =>
                setRightPanel((p) => (p === "preference" ? "none" : "preference"))
              }
              onOpenItinerary={() =>
                setRightPanel((p) => (p === "itinerary" ? "none" : "itinerary"))
              }
              onOpenRaw={() => setRightPanel((p) => (p === "raw" ? "none" : "raw"))}
              onOpenCanvas={() => setRightPanel((p) => (p === "canvas" ? "none" : "canvas"))}
            />
          ) : (
            <ChatPanel
              onOpenRaw={() => setRightPanel((p) => (p === "raw" ? "none" : "raw"))}
              onOpenCanvas={() => setRightPanel((p) => (p === "canvas" ? "none" : "canvas"))}
            />
          )}
        </div>
        {rightPanel === "raw" && (
          <div
            className="w-full sm:w-[520px] shrink-0 overflow-hidden animate-slide-in-right"
            style={{ borderLeft: "1px solid var(--border)" }}
          >
            <RawMessagesPanel onClose={() => setRightPanel("none")} />
          </div>
        )}
        {rightPanel === "canvas" && (
          <div
            className="w-full sm:w-[520px] shrink-0 overflow-hidden animate-slide-in-right"
            style={{ borderLeft: "1px solid var(--border)" }}
          >
            <CanvasPanel onClose={() => setRightPanel("none")} />
          </div>
        )}
        {rightPanel === "preference" && (
          <div
            className="w-full sm:w-[400px] lg:w-[400px] shrink-0 overflow-hidden animate-slide-in-right"
            style={{ borderLeft: "1px solid var(--border)" }}
          >
            <PreferenceSidebar onClose={() => setRightPanel("none")} />
          </div>
        )}
        {rightPanel === "itinerary" && (
          <div
            className="w-full sm:w-[400px] lg:w-[420px] shrink-0 overflow-hidden animate-slide-in-right"
            style={{ borderLeft: "1px solid var(--border)" }}
          >
            <ItineraryPanel
              onClose={() => setRightPanel("none")}
              onOpenCanvas={() => setRightPanel("canvas")}
            />
          </div>
        )}
      </div>
      <ToastStack />
    </div>
  );
}
