"use client";

import { useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AlertTriangle, Key, Copy, Check } from "lucide-react";
import type { ChatMessage as ChatMessageType } from "@/lib/store";
import ThoughtChain from "./ThoughtChain";
import RetrievalCard from "./RetrievalCard";

function CodeBlock({ className, children }: { className?: string; children?: React.ReactNode }) {
  const match = /language-(\w+)/.exec(className || "");
  const lang = match ? match[1] : "";
  const code = String(children).replace(/\n$/, "");
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [code]);

  if (!className) return <code>{children}</code>;

  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        <span className="code-block-lang">{lang || "code"}</span>
        <button onClick={handleCopy} className="code-block-copy" title="Copy code">
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>
      <pre><code>{children}</code></pre>
    </div>
  );
}

interface Props {
  message: ChatMessageType;
}

function formatTime(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

function isAuthError(content: string): boolean {
  return /401|authentication.?fail|invalid.*api.?key|api.?key.*invalid/i.test(content);
}

export default function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";
  const displayContent = isUser
    ? message.content
    : message.content
        .replace(/<openclaw-canvas>[\s\S]*?<\/openclaw-canvas>/g, "")  // complete tags
        .replace(/<openclaw-canvas>[\s\S]*$/g, "")                     // incomplete (streaming)
        .trim();
  const hasAuthError = !isUser && isAuthError(message.content);

  return (
    <div className="animate-fade-in">
      <div className="max-w-3xl mx-auto">
        {isUser ? (
          /* User message — right-aligned bubble */
          <div className="flex justify-end">
            <div className="max-w-[70%]">
              <div
                className="px-5 py-3 rounded-2xl rounded-tr-sm text-[14px] leading-relaxed shadow-sm"
                style={{ background: "var(--bubble-user)", border: "1px solid var(--border-accent)", color: "var(--text-primary)" }}
              >
                {message.content}
              </div>
              <div className="text-[10px] font-mono mt-1 text-right pr-1" style={{ color: "var(--text-muted)" }}>
                {formatTime(message.timestamp)}
              </div>
            </div>
          </div>
        ) : (
          /* Assistant message — left-aligned */
          <div className="flex gap-3 max-w-[85%]">
            <div className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center mt-0.5 shadow-sm" style={{ background: "var(--accent)" }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="white" fillOpacity="0.9" />
                <path d="M2 17L12 22L22 17" stroke="white" strokeOpacity="0.7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M2 12L12 17L22 12" stroke="white" strokeOpacity="0.85" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              {/* Tool calls */}
              {message.toolCalls && message.toolCalls.length > 0 && (
                <ThoughtChain toolCalls={message.toolCalls} />
              )}

              {/* Auth error alert */}
              {hasAuthError ? (
                <AuthErrorAlert content={message.content} />
              ) : displayContent ? (
                <div>
                  <div
                    className="px-5 py-3 rounded-2xl rounded-tl-sm text-[14px] leading-relaxed shadow-sm"
                    style={{ background: "var(--bubble-ai)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                  >
                    <div className="markdown-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ code: CodeBlock }}>
                        {displayContent}
                      </ReactMarkdown>
                    </div>
                  </div>
                  {message.retrievals && message.retrievals.length > 0 && (
                    <RetrievalCard retrievals={message.retrievals} />
                  )}
                  <div className="text-[10px] font-mono mt-1 pl-1" style={{ color: "var(--text-muted)" }}>
                    {formatTime(message.timestamp)}
                  </div>
                </div>
              ) : (
                /* Typing indicator */
                <div
                  className="px-4 py-3 rounded-2xl rounded-tl-sm inline-flex items-center gap-1.5 shadow-sm"
                  style={{ background: "var(--bubble-ai)", border: "1px solid var(--border)" }}
                >
                  <span className="typing-dot w-1.5 h-1.5 rounded-full" style={{ background: "var(--accent)" }} />
                  <span className="typing-dot w-1.5 h-1.5 rounded-full" style={{ background: "var(--accent)" }} />
                  <span className="typing-dot w-1.5 h-1.5 rounded-full" style={{ background: "var(--accent)" }} />
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function AuthErrorAlert({ content }: { content: string }) {
  return (
    <div className="animate-fade-in-scale rounded-xl border border-red-200 bg-red-50/80 px-4 py-3 space-y-2">
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
        <span className="text-[13px] font-semibold text-red-700">API Key 认证失败</span>
      </div>
      <p className="text-[12px] text-red-600/80 leading-relaxed">
        你的 API Key 无效或未配置。请检查 <code className="bg-red-100 px-1 rounded text-red-700">backend/.env</code> 文件中的配置。
      </p>
      <div className="flex items-center gap-3 pt-1">
        <a
          href="http://localhost:8002/"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-[11px] font-medium text-red-600 hover:text-red-800 transition-colors"
        >
          <Key className="w-3 h-3" />
          检查后端状态
        </a>
        <span className="text-[10px] text-red-400">|</span>
        <span className="text-[10px] text-red-500 font-mono">{content.slice(0, 120)}...</span>
      </div>
    </div>
  );
}
