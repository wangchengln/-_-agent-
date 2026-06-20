"use client";

import { useState, useRef, useEffect } from "react";
import { X, Sparkles, Loader2, CheckCircle2, Terminal, ChevronDown, ChevronRight } from "lucide-react";
import { streamChat } from "@/lib/api";
import ConfirmDialog from "@/components/shared/ConfirmDialog";

interface Props {
  content: string;
  fileName: string;
  onClose: () => void;
  onApply: (optimized: string) => void;
}

interface ToolLogEntry {
  type: "tool_start" | "tool_end" | "thinking";
  tool?: string;
  input?: string;
  output?: string;
  text?: string;
}

export default function OptimizeModal({ content, fileName, onClose, onApply }: Props) {
  const [resultText, setResultText] = useState("");
  const [processLog, setProcessLog] = useState<ToolLogEntry[]>([]);
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [processOpen, setProcessOpen] = useState(true);
  const outputRef = useRef<HTMLTextAreaElement>(null);
  const processRef = useRef<HTMLDivElement>(null);

  // Auto-scroll result during generation
  useEffect(() => {
    if (generating && outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [resultText, generating]);

  // Auto-scroll process log
  useEffect(() => {
    if (generating && processRef.current) {
      processRef.current.scrollTop = processRef.current.scrollHeight;
    }
  }, [processLog, generating]);

  const handleGenerate = async () => {
    if (generating) return;
    setGenerating(true);
    setResultText("");
    setProcessLog([]);
    setGenerated(false);
    setProcessOpen(true);

    const sessionId = `_ai_optimize_${Date.now()}`;
    const prompt = `请帮我优化以下记忆文件 "${fileName}" 的内容。

优化要求：
1. 保持原有信息不丢失
2. 提高信息密度，删除冗余内容
3. 改善结构和层次，使用清晰的标题和分类
4. 使用简洁的语言表达
5. 保持 Markdown 格式

当前文件内容：
\`\`\`
${content}
\`\`\`

请直接输出优化后的完整文件内容。不要添加任何额外解释，不要用代码块包裹，直接输出可以替换原文件的纯内容。`;

    try {
      // Track segments: last segment = final result, previous = process
      let segments: string[] = [""];
      let currentSegment = 0;

      for await (const event of streamChat(prompt, sessionId)) {
        if (event.event === "token") {
          const tok = (event.data.content as string) || "";
          segments[currentSegment] += tok;
          // Always update result with current (latest) segment
          setResultText(segments[currentSegment]);
        } else if (event.event === "new_response") {
          // Current segment was not final — move it to process
          const prevText = segments[currentSegment];
          if (prevText.trim()) {
            setProcessLog((prev) => [...prev, { type: "thinking", text: prevText }]);
          }
          currentSegment++;
          segments.push("");
          setResultText("");
        } else if (event.event === "tool_start") {
          setProcessLog((prev) => [
            ...prev,
            { type: "tool_start", tool: event.data.tool as string, input: event.data.input as string },
          ]);
        } else if (event.event === "tool_end") {
          setProcessLog((prev) => [
            ...prev,
            { type: "tool_end", tool: event.data.tool as string, output: event.data.output as string },
          ]);
        } else if (event.event === "error") {
          setResultText((prev) => prev + `\n\n[错误: ${event.data.error}]`);
          break;
        } else if (event.event === "done") {
          break;
        }
      }

      // Clean up result — remove code block wrappers
      let cleaned = segments[currentSegment].trim();
      if (cleaned.startsWith("```markdown")) cleaned = cleaned.slice(11);
      else if (cleaned.startsWith("```md")) cleaned = cleaned.slice(5);
      else if (cleaned.startsWith("```")) cleaned = cleaned.slice(3);
      if (cleaned.endsWith("```")) cleaned = cleaned.slice(0, -3);
      cleaned = cleaned.trim();
      if (cleaned) setResultText(cleaned);
      setGenerated(true);
      setProcessOpen(false);
    } catch {
      setResultText((prev) => prev + "\n\n[连接失败，请检查后端服务]");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 animate-fade-in" style={{ background: "rgba(0,0,0,0.5)" }}>
      <div className="w-full max-w-6xl rounded-xl shadow-2xl flex flex-col overflow-hidden" style={{ background: "var(--bg-surface)", height: "85vh" }}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5" style={{ color: "var(--accent)" }} />
            <span className="text-[16px] font-semibold" style={{ color: "var(--text-primary)" }}>
              AI 优化 — {fileName}
            </span>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-md transition-colors hover:opacity-80" style={{ color: "var(--text-muted)" }}>
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content — two columns */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left: Current content (read-only) */}
          <div className="flex-1 flex flex-col overflow-hidden" style={{ borderRight: "1px solid var(--border)" }}>
            <div className="px-4 py-2 text-[12px] font-semibold shrink-0" style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border)" }}>
              当前内容 (只读)
            </div>
            <pre className="flex-1 overflow-auto p-4 text-[12px] font-mono leading-relaxed whitespace-pre-wrap" style={{ color: "var(--text-secondary)", background: "var(--bg-editor)" }}>
              {content.split("\n").map((line, i) => (
                <div key={i} className="flex">
                  <span className="w-8 text-right mr-3 select-none shrink-0" style={{ color: "var(--text-muted)" }}>{i + 1}</span>
                  <span>{line}</span>
                </div>
              ))}
            </pre>
          </div>

          {/* Center divider with generate button */}
          <div className="flex flex-col items-center justify-center w-12 shrink-0" style={{ background: "var(--bg-page)" }}>
            <div className="w-px flex-1" style={{ background: "var(--border)" }} />
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="my-2 w-9 h-9 rounded-full flex items-center justify-center text-white shadow-lg transition-all hover:scale-110 active:scale-95 disabled:opacity-50"
              style={{ background: "var(--accent)" }}
              title="生成优化"
            >
              {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : generated ? <CheckCircle2 className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
            </button>
            <div className="w-px flex-1" style={{ background: "var(--border)" }} />
          </div>

          {/* Right: Process log + Result */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Process log (collapsible) */}
            {processLog.length > 0 && (
              <div className="shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
                <button
                  onClick={() => setProcessOpen(!processOpen)}
                  className="w-full px-4 py-1.5 flex items-center gap-1.5 text-[11px] font-semibold transition-colors hover:opacity-80"
                  style={{ color: "var(--text-muted)", background: "var(--bg-page)" }}
                >
                  {processOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                  AI 思考过程 ({processLog.length})
                  {generating && <Loader2 className="w-3 h-3 animate-spin ml-1" style={{ color: "var(--accent)" }} />}
                </button>
                {processOpen && (
                  <div ref={processRef} className="max-h-[180px] overflow-y-auto px-3 py-2 space-y-1" style={{ background: "var(--bg-page)" }}>
                    {processLog.map((entry, i) => (
                      <ProcessLogEntry key={i} entry={entry} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Result header */}
            <div className="px-4 py-2 text-[12px] font-semibold shrink-0 flex items-center gap-2" style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border)" }}>
              AI 优化建议
              {generating && !resultText && <Loader2 className="w-3 h-3 animate-spin" style={{ color: "var(--accent)" }} />}
            </div>

            {/* Result textarea */}
            <textarea
              ref={outputRef}
              className="flex-1 p-4 text-[12px] font-mono leading-relaxed resize-none outline-none"
              style={{ background: "var(--bg-editor)", color: "var(--text-primary)" }}
              value={resultText}
              onChange={(e) => setResultText(e.target.value)}
              placeholder="点击中间按钮，AI 将分析当前文件并生成优化建议..."
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3 shrink-0" style={{ borderTop: "1px solid var(--border)" }}>
          <div className="flex items-center gap-4 text-[11px]" style={{ color: "var(--text-muted)" }}>
            {generated && (
              <>
                <span>原始: {content.length} 字符</span>
                <span>优化后: {resultText.length} 字符</span>
                {content.length > 0 && (
                  <span className={content.length > resultText.length ? "text-emerald-500" : ""}>
                    {content.length > resultText.length
                      ? `精简 ${Math.round((1 - resultText.length / content.length) * 100)}%`
                      : `增加 ${Math.round((resultText.length / content.length - 1) * 100)}%`}
                  </span>
                )}
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onClose} className="px-4 py-1.5 text-[12px] font-medium rounded-lg" style={{ color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
              取消
            </button>
            <button
              onClick={() => { if (generated && resultText) setShowConfirm(true); }}
              disabled={!generated || !resultText}
              className="px-4 py-1.5 text-[12px] font-medium text-white rounded-lg disabled:opacity-40"
              style={{ background: "var(--accent)" }}
            >
              确认覆盖
            </button>
          </div>
        </div>
      </div>

      {showConfirm && (
        <ConfirmDialog
          title="确定要覆盖原始文档吗？"
          message="此操作将用 AI 优化内容替换当前文件内容。修改后需要手动保存。"
          confirmText="确认覆盖"
          onConfirm={() => { setShowConfirm(false); onApply(resultText); }}
          onCancel={() => setShowConfirm(false)}
        />
      )}
    </div>
  );
}

function ProcessLogEntry({ entry }: { entry: ToolLogEntry }) {
  if (entry.type === "thinking") {
    return (
      <div className="text-[10px] leading-relaxed py-0.5" style={{ color: "var(--text-muted)" }}>
        {(entry.text || "").slice(0, 200)}{(entry.text || "").length > 200 ? "..." : ""}
      </div>
    );
  }
  if (entry.type === "tool_start") {
    return (
      <div className="flex items-center gap-1.5 text-[10px] py-0.5">
        <Terminal className="w-3 h-3 shrink-0" style={{ color: "var(--accent)" }} />
        <span className="font-mono font-medium" style={{ color: "var(--accent)" }}>{entry.tool}</span>
        {entry.input && (
          <span className="truncate" style={{ color: "var(--text-muted)" }}>
            {entry.input.slice(0, 80)}{entry.input.length > 80 ? "..." : ""}
          </span>
        )}
      </div>
    );
  }
  if (entry.type === "tool_end") {
    return (
      <div className="flex items-center gap-1.5 text-[10px] py-0.5">
        <CheckCircle2 className="w-3 h-3 shrink-0 text-emerald-500" />
        <span className="font-mono" style={{ color: "var(--text-muted)" }}>{entry.tool} done</span>
      </div>
    );
  }
  return null;
}
