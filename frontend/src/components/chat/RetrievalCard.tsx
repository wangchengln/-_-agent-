"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Database } from "lucide-react";
import type { RetrievalResult } from "@/lib/store";

interface Props {
  retrievals: RetrievalResult[];
}

export default function RetrievalCard({ retrievals }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (retrievals.length === 0) return null;

  return (
    <div className="mt-1.5 mb-2 rounded-xl overflow-hidden animate-fade-in-scale" style={{ border: "1px solid var(--border-accent)", background: "var(--accent-bg)" }}>
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-1.5 text-[12px] hover:opacity-80 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="w-3 h-3" style={{ color: "var(--accent)" }} />
        ) : (
          <ChevronRight className="w-3 h-3" style={{ color: "var(--accent)" }} />
        )}
        <div className="w-5 h-5 rounded flex items-center justify-center" style={{ background: "var(--accent-bg)" }}>
          <Database className="w-3 h-3" style={{ color: "var(--accent)" }} />
        </div>
        <span className="font-medium" style={{ color: "var(--accent)" }}>Memory Retrieval</span>
        <span className="text-[10px] ml-1" style={{ color: "var(--text-muted)" }}>
          {retrievals.length} snippet{retrievals.length > 1 ? "s" : ""}
        </span>
      </button>
      {expanded && (
        <div className="px-3 pb-2.5 space-y-2 pt-2" style={{ borderTop: "1px solid var(--border-accent)" }}>
          {retrievals.map((r, idx) => (
            <div key={idx} className="space-y-0.5">
              <div className="flex items-center gap-2 text-[10px]">
                <span className="font-semibold uppercase tracking-wider" style={{ color: "var(--accent)" }}>
                  {r.source}
                </span>
                <span style={{ color: "var(--text-muted)" }}>score: {r.score}</span>
              </div>
              <pre className="p-2 rounded-lg text-[11px] font-mono whitespace-pre-wrap leading-relaxed max-h-32 overflow-y-auto" style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
                {r.text}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
