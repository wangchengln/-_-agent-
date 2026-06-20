"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { readFile, saveFile } from "@/lib/api";
import { useTheme } from "@/lib/theme";
import {
  Save, FileText, Loader2, CheckCircle2, AlertCircle, Zap,
} from "lucide-react";
import dynamic from "next/dynamic";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full" style={{ color: "var(--text-muted)" }}>
      <Loader2 className="w-4 h-4 animate-spin mr-2" />Loading editor...
    </div>
  ),
});

interface Props {
  skill: { name: string; path: string } | null;
}

export default function SkillEditor({ skill }: Props) {
  const { theme } = useTheme();
  const [content, setContent] = useState("");
  const [originalContent, setOriginalContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved" | "error">("idle");
  const editorRef = useRef<unknown>(null);

  useEffect(() => {
    if (!skill) {
      setContent("");
      setOriginalContent("");
      return;
    }
    setLoading(true);
    setSaveStatus("idle");
    readFile(skill.path)
      .then((t) => { setContent(t); setOriginalContent(t); })
      .catch(() => { setContent("# Error loading file"); setOriginalContent(""); })
      .finally(() => setLoading(false));
  }, [skill]);

  const handleSave = useCallback(async () => {
    if (!skill || saving) return;
    setSaving(true);
    setSaveStatus("idle");
    try {
      await saveFile(skill.path, content);
      setOriginalContent(content);
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch {
      setSaveStatus("error");
    } finally {
      setSaving(false);
    }
  }, [skill, content, saving]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [handleSave]);

  const isDirty = content !== originalContent;
  const fileName = skill?.path.split("/").pop() || "";
  const skillDir = skill?.path.replace(/\/[^/]+$/, "") || "";

  if (!skill) {
    return (
      <div className="flex flex-col items-center justify-center h-full" style={{ color: "var(--text-muted)" }}>
        <Zap className="w-10 h-10 mb-2" style={{ color: "var(--border)" }} />
        <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>未选择技能</p>
        <p className="text-[11px] mt-1">从左侧技能库选择一个技能</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Breadcrumb */}
      <div className="h-8 flex items-center px-4 text-[11px] font-mono shrink-0" style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border)" }}>
        {skillDir.split("/").map((part, i, arr) => (
          <span key={i}>
            {part}
            {i < arr.length - 1 && <span className="mx-1">/</span>}
          </span>
        ))}
        <span className="mx-1">/</span>
      </div>

      {/* Tab bar */}
      <div className="h-10 flex items-center justify-between px-3 shrink-0" style={{ borderBottom: "1px solid var(--border)", background: "var(--bg-surface)" }}>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-md text-[12px] font-medium" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
            <FileText className="w-3 h-3" />
            {fileName}
            {isDirty && <span className="w-1.5 h-1.5 bg-amber-400 rounded-full" />}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {saveStatus === "saved" && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />}
          {saveStatus === "error" && <AlertCircle className="w-3.5 h-3.5 text-red-500" />}
          <button
            onClick={handleSave}
            disabled={saving || !isDirty}
            className="flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium text-white disabled:opacity-25 transition-all active:scale-95"
            style={{ background: "var(--accent)" }}
            title="Save (Ctrl+S)"
          >
            {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
            Save
          </button>
        </div>
      </div>

      {/* Monaco editor */}
      <div className="flex-1" style={{ background: "var(--bg-editor)" }}>
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--text-muted)" }} />
          </div>
        ) : (
          <MonacoEditor
            height="100%"
            language="markdown"
            value={content}
            theme={theme === "dark" ? "vs-dark" : "vs"}
            onChange={(val) => setContent(val || "")}
            onMount={(editor) => { editorRef.current = editor; }}
            options={{
              minimap: { enabled: false },
              fontSize: 13,
              lineNumbers: "on",
              wordWrap: "on",
              scrollBeyondLastLine: false,
              padding: { top: 10, bottom: 10 },
              renderLineHighlight: "none",
              overviewRulerBorder: false,
              hideCursorInOverviewRuler: true,
              automaticLayout: true,
              fontFamily: "'SF Mono','JetBrains Mono','Fira Code',Consolas,monospace",
              lineHeight: 20,
              cursorBlinking: "smooth",
              smoothScrolling: true,
            }}
          />
        )}
      </div>

      {/* Editor status bar */}
      <div className="h-6 flex items-center justify-between px-3 text-[10px] shrink-0" style={{ background: "var(--accent)", color: "white" }}>
        <div className="flex items-center gap-3">
          <span>UTF-8</span>
          <span>Markdown</span>
        </div>
        <div className="flex items-center gap-3">
          <span>{isDirty ? "Unsaved" : "Synced"}</span>
        </div>
      </div>
    </div>
  );
}
