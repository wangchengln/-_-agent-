"use client";

import { useState, useRef, useEffect } from "react";
import { X, FolderOpen, Sparkles, Plus, ExternalLink, Upload, Loader2, FileText, CheckCircle2, Terminal, ChevronDown, ChevronRight } from "lucide-react";
import { saveFile, streamChat } from "@/lib/api";

interface Props {
  onClose: () => void;
  onCreated: () => void;
}

interface UploadedFile {
  relativePath: string;
  content: string;
}

interface AiLogEntry {
  type: "tool_start" | "tool_end" | "thinking";
  tool?: string;
  input?: string;
  output?: string;
  text?: string;
}

const SKILL_TEMPLATE = `---
name: "{name}"
description: "Skill description here"
---

# {name}

## 触发条件
当用户请求与 {name} 相关的操作时触发。

## 执行步骤
1. 读取用户输入
2. 处理请求
3. 返回结果

## 示例对话
**用户**: 请使用 {name}
**Agent**: 好的，正在执行 {name}...
`;

function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsText(file);
  });
}

export default function NewSkillModal({ onClose, onCreated }: Props) {
  const [skillName, setSkillName] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [creating, setCreating] = useState(false);
  const folderInputRef = useRef<HTMLInputElement>(null);

  // AI creation state
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiResultText, setAiResultText] = useState("");
  const [aiProcessLog, setAiProcessLog] = useState<AiLogEntry[]>([]);
  const [aiDone, setAiDone] = useState(false);
  const [processOpen, setProcessOpen] = useState(true);
  const processRef = useRef<HTMLDivElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  // Auto-scroll process log
  useEffect(() => {
    if (aiGenerating && processRef.current) {
      processRef.current.scrollTop = processRef.current.scrollHeight;
    }
  }, [aiProcessLog, aiGenerating]);

  // Auto-scroll result
  useEffect(() => {
    if (aiGenerating && resultRef.current) {
      resultRef.current.scrollTop = resultRef.current.scrollHeight;
    }
  }, [aiResultText, aiGenerating]);

  // Handle folder selection
  const handleFolderUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const entries: UploadedFile[] = [];
    let folderName = "";

    for (const file of Array.from(files)) {
      const path = (file as unknown as { webkitRelativePath: string }).webkitRelativePath || file.name;
      if (!folderName) {
        folderName = path.split("/")[0];
      }
      try {
        const content = await readFileAsText(file);
        const relativePath = path.split("/").slice(1).join("/");
        if (relativePath) {
          entries.push({ relativePath, content });
        }
      } catch {
        // Skip files that can't be read as text
      }
    }

    if (folderName && !skillName) {
      setSkillName(folderName);
    }
    setUploadedFiles(entries);
  };

  // Create skill (manual — with or without uploaded files)
  const handleCreate = async () => {
    const name = skillName.trim();
    if (!name || creating) return;
    setCreating(true);
    try {
      if (uploadedFiles.length > 0) {
        // Upload all files to skills/{name}/
        for (const f of uploadedFiles) {
          await saveFile(`skills/${name}/${f.relativePath}`, f.content);
        }
        // Ensure SKILL.md exists
        const hasSkillMd = uploadedFiles.some(
          (f) => f.relativePath === "SKILL.md" || f.relativePath.endsWith("/SKILL.md")
        );
        if (!hasSkillMd) {
          const content = SKILL_TEMPLATE.replaceAll("{name}", name);
          await saveFile(`skills/${name}/SKILL.md`, content);
        }
      } else {
        // Create empty template
        const content = SKILL_TEMPLATE.replaceAll("{name}", name);
        await saveFile(`skills/${name}/SKILL.md`, content);
      }
      onCreated();
    } catch {
      // error handled silently
    } finally {
      setCreating(false);
    }
  };

  // AI-powered skill creation with process/result split
  const handleAiGenerate = async () => {
    const desc = aiPrompt.trim();
    if (!desc || aiGenerating) return;
    setAiGenerating(true);
    setAiResultText("");
    setAiProcessLog([]);
    setAiDone(false);
    setProcessOpen(true);

    const sessionId = `_ai_skill_${Date.now()}`;
    const prompt = `请为我创建一个新的Agent技能。以下是用户的需求描述：

"${desc}"

请按照以下步骤操作：
1. 根据需求确定一个合适的英文技能名称（用下划线分隔，如 weather_query）
2. 在 skills/ 目录下创建对应的文件夹
3. 在文件夹中创建 SKILL.md 文件，包含完整的技能定义

SKILL.md 格式要求：
- 开头为 YAML frontmatter（包含 name 和 description 字段）
- 正文包含：触发条件、执行步骤（详细的指令）、输出格式、示例对话
- 指令应详细、可操作，让 Agent 能够按照步骤执行

请直接创建文件，完成后告诉我技能名称和简要说明。`;

    try {
      let segments: string[] = [""];
      let currentSegment = 0;

      for await (const event of streamChat(prompt, sessionId)) {
        if (event.event === "token") {
          const tok = (event.data.content as string) || "";
          segments[currentSegment] += tok;
          setAiResultText(segments[currentSegment]);
        } else if (event.event === "new_response") {
          const prevText = segments[currentSegment];
          if (prevText.trim()) {
            setAiProcessLog((prev) => [...prev, { type: "thinking", text: prevText }]);
          }
          currentSegment++;
          segments.push("");
          setAiResultText("");
        } else if (event.event === "tool_start") {
          setAiProcessLog((prev) => [
            ...prev,
            { type: "tool_start", tool: event.data.tool as string, input: event.data.input as string },
          ]);
        } else if (event.event === "tool_end") {
          setAiProcessLog((prev) => [
            ...prev,
            { type: "tool_end", tool: event.data.tool as string, output: event.data.output as string },
          ]);
        } else if (event.event === "error") {
          setAiResultText((prev) => prev + `\n\n[错误: ${event.data.error}]`);
          break;
        } else if (event.event === "done") {
          break;
        }
      }

      setAiDone(true);
      setProcessOpen(false);
    } catch {
      setAiResultText((prev) => prev + "\n\n[连接失败，请检查后端服务]");
    } finally {
      setAiGenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 animate-fade-in" style={{ background: "rgba(0,0,0,0.5)" }}>
      <div className="w-[850px] max-h-[85vh] rounded-xl shadow-2xl overflow-hidden flex flex-col" style={{ background: "var(--bg-surface)" }}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2">
            <Plus className="w-5 h-5" style={{ color: "var(--accent)" }} />
            <span className="text-[16px] font-semibold" style={{ color: "var(--text-primary)" }}>创建新的技能</span>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-md transition-colors hover:opacity-80" style={{ color: "var(--text-muted)" }}>
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content — two columns */}
        <div className="flex-1 flex relative overflow-hidden" style={{ minHeight: 360 }}>
          {/* Left: Manual creation */}
          <div className="flex-1 p-6 space-y-4 overflow-y-auto">
            <div className="flex items-center gap-2 mb-1">
              <FolderOpen className="w-5 h-5" style={{ color: "var(--accent)" }} />
              <span className="text-[14px] font-semibold" style={{ color: "var(--text-primary)" }}>手动创建</span>
            </div>
            <p className="text-[12px] leading-relaxed" style={{ color: "var(--text-muted)" }}>
              上传一个技能文件夹，或直接输入名称创建空模板。
            </p>

            <div>
              <label className="text-[11px] font-semibold mb-1 block" style={{ color: "var(--text-secondary)" }}>技能名称</label>
              <input
                type="text"
                value={skillName}
                onChange={(e) => setSkillName(e.target.value)}
                placeholder="my_new_skill"
                className="w-full px-3 py-2 rounded-lg text-[13px] font-mono outline-none transition-all"
                style={{ background: "var(--bg-page)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
              />
            </div>

            {/* Folder upload zone */}
            <div
              onClick={() => folderInputRef.current?.click()}
              className="border-2 border-dashed rounded-lg p-5 text-center transition-all cursor-pointer hover:shadow-sm"
              style={{ borderColor: uploadedFiles.length > 0 ? "var(--accent)" : "var(--border)" }}
            >
              <input
                ref={folderInputRef}
                type="file"
                className="hidden"
                onChange={handleFolderUpload}
                {...({ webkitdirectory: "", directory: "", multiple: true } as React.InputHTMLAttributes<HTMLInputElement>)}
              />
              {uploadedFiles.length > 0 ? (
                <div>
                  <CheckCircle2 className="w-7 h-7 mx-auto mb-2" style={{ color: "var(--accent)" }} />
                  <p className="text-[12px] font-medium" style={{ color: "var(--accent)" }}>
                    已选择 {uploadedFiles.length} 个文件
                  </p>
                  <div className="mt-2 space-y-0.5 max-h-24 overflow-y-auto">
                    {uploadedFiles.slice(0, 8).map((f, i) => (
                      <div key={i} className="flex items-center gap-1 text-[10px] justify-center" style={{ color: "var(--text-muted)" }}>
                        <FileText className="w-3 h-3" />
                        {f.relativePath}
                      </div>
                    ))}
                    {uploadedFiles.length > 8 && (
                      <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>...还有 {uploadedFiles.length - 8} 个文件</p>
                    )}
                  </div>
                </div>
              ) : (
                <div>
                  <Upload className="w-7 h-7 mx-auto mb-2" style={{ color: "var(--text-muted)" }} />
                  <p className="text-[12px] font-medium" style={{ color: "var(--text-secondary)" }}>点击上传技能文件夹</p>
                  <p className="text-[10px] mt-1" style={{ color: "var(--text-muted)" }}>文件夹名将自动填入技能名称</p>
                </div>
              )}
            </div>

            <button
              onClick={handleCreate}
              disabled={!skillName.trim() || creating}
              className="w-full py-2.5 rounded-lg text-[13px] font-medium transition-all disabled:opacity-40"
              style={{ border: "1px solid var(--border)", color: "var(--text-secondary)" }}
            >
              {creating ? (
                <span className="flex items-center justify-center gap-1.5">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  创建中...
                </span>
              ) : (
                uploadedFiles.length > 0 ? "创建技能" : "创建空模板"
              )}
            </button>
          </div>

          {/* Divider */}
          <div className="absolute left-1/2 top-4 bottom-4 w-px" style={{ background: "var(--border)" }} />

          {/* Right: AI creation */}
          <div className="flex-1 p-6 space-y-4 overflow-y-auto flex flex-col">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-6 h-6 rounded flex items-center justify-center" style={{ background: "linear-gradient(135deg, var(--accent), var(--accent-hover))" }}>
                <Sparkles className="w-3.5 h-3.5 text-white" />
              </div>
              <span className="text-[14px] font-semibold" style={{ color: "var(--text-primary)" }}>自动 AI 创建</span>
            </div>
            <p className="text-[12px] leading-relaxed" style={{ color: "var(--text-muted)" }}>
              用自然语言描述你需要的技能，AI 将自动生成完整技能。
            </p>

            <div>
              <label className="text-[11px] font-semibold mb-1 block" style={{ color: "var(--text-secondary)" }}>描述你的技能</label>
              <textarea
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value.slice(0, 500))}
                placeholder="例如：创建一个天气查询技能，可以获取指定城市的天气信息..."
                rows={3}
                disabled={aiGenerating}
                className="w-full px-3 py-2 rounded-lg text-[13px] outline-none resize-none disabled:opacity-50"
                style={{ background: "var(--bg-page)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
              />
              <span className="text-[10px] float-right mt-0.5" style={{ color: "var(--text-muted)" }}>{aiPrompt.length}/500</span>
            </div>

            {/* AI process log (collapsible) */}
            {aiProcessLog.length > 0 && (
              <div className="shrink-0 rounded-lg overflow-hidden" style={{ border: "1px solid var(--border)" }}>
                <button
                  onClick={() => setProcessOpen(!processOpen)}
                  className="w-full px-3 py-1.5 flex items-center gap-1.5 text-[11px] font-semibold transition-colors hover:opacity-80"
                  style={{ color: "var(--text-muted)", background: "var(--bg-page)" }}
                >
                  {processOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                  AI 创建过程 ({aiProcessLog.length})
                  {aiGenerating && <Loader2 className="w-3 h-3 animate-spin ml-1" style={{ color: "var(--accent)" }} />}
                </button>
                {processOpen && (
                  <div ref={processRef} className="max-h-[120px] overflow-y-auto px-3 py-2 space-y-1" style={{ background: "var(--bg-page)" }}>
                    {aiProcessLog.map((entry, i) => (
                      <AiProcessLogEntry key={i} entry={entry} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* AI result area */}
            {(aiResultText || aiGenerating) && (
              <div ref={resultRef} className="flex-1 min-h-[100px] max-h-[160px] overflow-y-auto rounded-lg p-3 text-[11px] font-mono leading-relaxed whitespace-pre-wrap"
                style={{ background: "var(--bg-page)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}
              >
                {aiResultText || (aiProcessLog.length === 0 ? "正在分析需求..." : "")}
                {aiGenerating && <span className="inline-block w-2 h-4 ml-0.5 animate-pulse" style={{ background: "var(--accent)" }} />}
              </div>
            )}

            <button
              onClick={aiDone ? () => { onCreated(); } : handleAiGenerate}
              disabled={aiGenerating || (!aiDone && !aiPrompt.trim())}
              className="w-full py-2.5 rounded-lg text-[13px] font-medium text-white transition-all disabled:opacity-40"
              style={{ background: "linear-gradient(135deg, var(--accent), var(--accent-hover))" }}
            >
              <span className="flex items-center justify-center gap-1.5">
                {aiGenerating ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    生成中...
                  </>
                ) : aiDone ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    完成，关闭
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    生成技能
                  </>
                )}
              </span>
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-center gap-4 px-6 py-3 shrink-0" style={{ borderTop: "1px solid var(--border)", background: "var(--bg-page)" }}>
          <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>推荐更多技能</span>
          <a href="https://github.com/anthropics/skills" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-[11px] transition-colors hover:opacity-80" style={{ color: "var(--accent)" }}>
            Anthropic 官方技能库 <ExternalLink className="w-3 h-3" />
          </a>
          <span style={{ color: "var(--border)" }}>|</span>
          <a href="https://clawhub.ai/" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-[11px] transition-colors hover:opacity-80" style={{ color: "var(--accent)" }}>
            OpenClaw 技能社区 <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  );
}

function AiProcessLogEntry({ entry }: { entry: AiLogEntry }) {
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
            {entry.input.slice(0, 60)}{entry.input.length > 60 ? "..." : ""}
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
