"use client";

import { useRef, useCallback, useEffect, useState } from "react";
import { X, ChevronRight, ChevronDown, BookOpen, List } from "lucide-react";

interface Chapter {
  id: string;
  label: string;
  title: string;
  src: string;
}

const CHAPTERS: Chapter[] = [
  {
    id: "ch1-1",
    label: "Ch 1.1",
    title: "Agent Skills：新一代开发范式",
    src: "/learn/ch1-1.html",
  },
  {
    id: "ch1-2",
    label: "Ch 1.2",
    title: "Agent Skills 基础实现方法详解",
    src: "/learn/ch1-2.html",
  },
  {
    id: "ch2-1",
    label: "Ch 2.1",
    title: "Agent Skills 官方范式深度解析",
    src: "/learn/ch2-1.html",
  },
  {
    id: "ch2-2",
    label: "Ch 2.2",
    title: "LangChain Agent Skills 开发实战",
    src: "/learn/ch2-2.html",
  },
  {
    id: "ch3-1",
    label: "Ch 3.1",
    title: "项目概述与架构设计",
    src: "/learn/ch3-1.html",
  },
  {
    id: "ch3-2",
    label: "Ch 3.2",
    title: "安装部署与使用指南",
    src: "/learn/ch3-2.html",
  },
  {
    id: "course-intro",
    label: "正课",
    title: "正课介绍与成果展示",
    src: "/learn/course-intro.html",
  },
];

interface Props {
  onClose: () => void;
}

export default function LearnPanel({ onClose }: Props) {
  const [width, setWidth] = useState(520);
  const [activeChapter, setActiveChapter] = useState(CHAPTERS[0]);
  const [tocOpen, setTocOpen] = useState(false);
  const dragging = useRef(false);
  const startX = useRef(0);
  const startW = useRef(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      dragging.current = true;
      startX.current = e.clientX;
      startW.current = width;
      document.body.style.userSelect = "none";
      document.body.style.cursor = "col-resize";
      if (iframeRef.current) {
        iframeRef.current.style.pointerEvents = "none";
      }
      e.preventDefault();
    },
    [width]
  );

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const delta = e.clientX - startX.current;
      const newW = Math.max(360, Math.min(900, startW.current + delta));
      setWidth(newW);
    };
    const onMouseUp = () => {
      if (!dragging.current) return;
      dragging.current = false;
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
      if (iframeRef.current) {
        iframeRef.current.style.pointerEvents = "";
      }
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  // Close TOC when clicking outside
  useEffect(() => {
    if (!tocOpen) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest("[data-toc-panel]") && !target.closest("[data-toc-toggle]")) {
        setTocOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [tocOpen]);

  const selectChapter = (ch: Chapter) => {
    setActiveChapter(ch);
    setTocOpen(false);
  };

  return (
    <div className="flex shrink-0 h-full animate-slide-in-left" style={{ width }}>
      <div
        className="flex flex-col flex-1 overflow-hidden relative"
        style={{
          background: "var(--bg-surface)",
          borderRight: "1px solid var(--border)",
        }}
      >
        {/* Header */}
        <div
          className="h-10 flex items-center gap-2 px-3 shrink-0"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          {/* TOC toggle */}
          <button
            data-toc-toggle
            onClick={() => setTocOpen((v) => !v)}
            className="p-1 rounded hover:opacity-80 transition-colors"
            style={{ color: "var(--accent)" }}
            title="章节目录"
          >
            <List className="w-4 h-4" />
          </button>

          {/* Chapter indicator */}
          <div className="flex items-center gap-1.5 flex-1 min-w-0">
            <span
              className="text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0"
              style={{
                background: "var(--accent-bg)",
                color: "var(--accent)",
              }}
            >
              {activeChapter.label}
            </span>
            <span
              className="text-[12px] font-medium truncate"
              style={{ color: "var(--text-primary)" }}
            >
              {activeChapter.title}
            </span>
          </div>

          {/* Close */}
          <button
            onClick={onClose}
            className="p-1 rounded hover:opacity-80 shrink-0"
            style={{ color: "var(--text-muted)" }}
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* TOC Overlay Panel */}
        {tocOpen && (
          <div
            data-toc-panel
            className="absolute top-10 left-0 z-20 w-full max-w-[320px] mx-2 rounded-lg shadow-lg overflow-hidden"
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border)",
              top: "44px",
              left: "8px",
            }}
          >
            {/* TOC Header */}
            <div
              className="px-3 py-2 flex items-center gap-2"
              style={{ borderBottom: "1px solid var(--border)" }}
            >
              <BookOpen className="w-3.5 h-3.5" style={{ color: "var(--accent)" }} />
              <span
                className="text-[11px] font-semibold uppercase tracking-wider"
                style={{ color: "var(--text-muted)" }}
              >
                课程目录
              </span>
            </div>

            {/* Chapter list */}
            <div className="py-1">
              {CHAPTERS.map((ch) => {
                const isActive = ch.id === activeChapter.id;
                return (
                  <button
                    key={ch.id}
                    onClick={() => selectChapter(ch)}
                    className="w-full text-left px-3 py-2.5 flex items-center gap-3 transition-colors"
                    style={{
                      background: isActive ? "var(--accent-bg)" : "transparent",
                      color: isActive ? "var(--accent)" : "var(--text-primary)",
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) e.currentTarget.style.background = "var(--bg-hover)";
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) e.currentTarget.style.background = "transparent";
                    }}
                  >
                    {/* Chapter number badge */}
                    <span
                      className="text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0"
                      style={{
                        background: isActive
                          ? "var(--accent)"
                          : "var(--accent-bg)",
                        color: isActive ? "#fff" : "var(--accent)",
                      }}
                    >
                      {ch.label}
                    </span>

                    {/* Title */}
                    <span className="text-[12px] font-medium flex-1">
                      {ch.title}
                    </span>

                    {/* Active indicator */}
                    {isActive && (
                      <ChevronRight
                        className="w-3.5 h-3.5 shrink-0"
                        style={{ color: "var(--accent)" }}
                      />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Content iframe */}
        <iframe
          ref={iframeRef}
          src={activeChapter.src}
          className="flex-1 w-full border-0"
          title={activeChapter.title}
          sandbox="allow-scripts allow-same-origin"
        />
      </div>

      {/* Drag handle */}
      <div
        className="w-[5px] cursor-col-resize flex items-center justify-center shrink-0 hover:bg-[var(--accent-bg)] transition-colors"
        onMouseDown={onMouseDown}
        style={{ background: "transparent" }}
      >
        <div
          className="w-[2px] h-8 rounded-full opacity-0 hover:opacity-100 transition-opacity"
          style={{ background: "var(--accent)" }}
        />
      </div>
    </div>
  );
}
