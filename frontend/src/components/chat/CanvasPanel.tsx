"use client";

import { useState, useEffect, useRef } from "react";
import { X, MonitorPlay, Code, Eye, Loader2 } from "lucide-react";
import { useApp } from "@/lib/store";

interface Props {
  onClose: () => void;
}

type ViewMode = "code" | "preview";

export default function CanvasPanel({ onClose }: Props) {
  const { canvasCode, canvasReady, canvasStreaming } = useApp();
  const [viewMode, setViewMode] = useState<ViewMode>("code");
  const codeEndRef = useRef<HTMLDivElement>(null);

  // Auto-switch to preview when canvas finishes
  useEffect(() => {
    if (canvasReady && canvasCode) {
      setViewMode("preview");
    }
  }, [canvasReady, canvasCode]);

  // Switch to code view when streaming starts
  useEffect(() => {
    if (canvasStreaming) {
      setViewMode("code");
    }
  }, [canvasStreaming]);

  // Auto-scroll code view during streaming
  useEffect(() => {
    if (viewMode === "code" && canvasStreaming && codeEndRef.current) {
      codeEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [canvasCode, viewMode, canvasStreaming]);

  const hasContent = canvasCode.length > 0;

  return (
    <div className="flex flex-col h-full" style={{ background: "var(--bg-surface)" }}>
      {/* Header */}
      <div
        className="h-14 flex items-center justify-between px-4 shrink-0"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-2">
          <MonitorPlay className="w-4 h-4" style={{ color: "var(--accent)" }} />
          <span className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
            Canvas
          </span>
          {canvasStreaming && (
            <div className="flex items-center gap-1.5 ml-1">
              <Loader2 className="w-3 h-3 animate-spin" style={{ color: "var(--accent)" }} />
              <span className="text-[10px]" style={{ color: "var(--accent)" }}>生成中...</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-1">
          {/* Code / Preview toggle */}
          {hasContent && (
            <div
              className="flex rounded-md overflow-hidden mr-2"
              style={{ border: "1px solid var(--border)" }}
            >
              <button
                onClick={() => setViewMode("code")}
                className="flex items-center gap-1 px-2.5 py-1 text-[11px] transition-colors"
                style={{
                  background: viewMode === "code" ? "var(--accent-bg)" : "transparent",
                  color: viewMode === "code" ? "var(--accent)" : "var(--text-muted)",
                }}
              >
                <Code className="w-3 h-3" />
                Code
              </button>
              <button
                onClick={() => setViewMode("preview")}
                className="flex items-center gap-1 px-2.5 py-1 text-[11px] transition-colors"
                style={{
                  background: viewMode === "preview" ? "var(--accent-bg)" : "transparent",
                  color: viewMode === "preview" ? "var(--accent)" : "var(--text-muted)",
                  borderLeft: "1px solid var(--border)",
                }}
              >
                <Eye className="w-3 h-3" />
                Preview
              </button>
            </div>
          )}
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg transition-colors hover:opacity-80"
            style={{ color: "var(--text-muted)" }}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      {!hasContent ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <MonitorPlay className="w-10 h-10 mx-auto mb-3" style={{ color: "var(--text-muted)", opacity: 0.4 }} />
            <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>
              暂无 Canvas 内容
            </p>
            <p className="text-[11px] mt-1" style={{ color: "var(--text-muted)", opacity: 0.7 }}>
              让 AI 生成网页、图表或互动内容后将在此预览
            </p>
          </div>
        </div>
      ) : viewMode === "code" ? (
        /* Code view — show raw HTML source streaming in */
        <div
          className="flex-1 overflow-auto p-4"
          style={{ background: "#1a1a2e" }}
        >
          <pre
            className="text-[12px] leading-relaxed whitespace-pre-wrap break-words"
            style={{ color: "#d4d4e8", fontFamily: '"SF Mono","JetBrains Mono","Fira Code",Consolas,monospace' }}
          >
            {canvasCode}
            {canvasStreaming && (
              <span className="inline-block w-2 h-4 ml-0.5 animate-pulse" style={{ background: "var(--accent)" }} />
            )}
            <div ref={codeEndRef} />
          </pre>
        </div>
      ) : (
        /* Preview view — render HTML in sandboxed iframe */
        <iframe
          srcDoc={canvasCode}
          sandbox="allow-scripts"
          className="flex-1 w-full border-0"
          style={{ background: "#ffffff" }}
          title="Canvas Preview"
        />
      )}

      {/* Footer */}
      <div
        className="shrink-0 px-4 py-2 flex items-center justify-between"
        style={{ borderTop: "1px solid var(--border)" }}
      >
        <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
          由 AI 生成 · sandbox 安全隔离
        </span>
        {hasContent && (
          <span className="text-[10px] font-mono" style={{ color: "var(--text-muted)" }}>
            {canvasCode.length.toLocaleString()} chars
          </span>
        )}
      </div>
    </div>
  );
}
