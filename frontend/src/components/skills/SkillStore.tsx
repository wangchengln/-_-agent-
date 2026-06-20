"use client";

import { useState, useEffect } from "react";
import { X, Download, Loader2, ExternalLink, Search, CheckCircle2, Globe, AlertCircle } from "lucide-react";
import { saveFile } from "@/lib/api";

interface Props {
  onClose: () => void;
  onInstalled: () => void;
}

interface RemoteSkill {
  name: string;
  description: string;
  source: "anthropic" | "community";
  repoUrl: string;
  downloadUrl: string;
}

interface GithubContent {
  name: string;
  type: string;
  path: string;
  download_url: string | null;
}

const ANTHROPIC_REPO = "anthropics/skills";
const ANTHROPIC_SKILLS_PATH = "skills";

export default function SkillStore({ onClose, onInstalled }: Props) {
  const [skills, setSkills] = useState<RemoteSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [installing, setInstalling] = useState<string | null>(null);
  const [installed, setInstalled] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchSkills();
  }, []);

  const fetchSkills = async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await fetch(
        `https://api.github.com/repos/${ANTHROPIC_REPO}/contents/${ANTHROPIC_SKILLS_PATH}`,
        { headers: { Accept: "application/vnd.github.v3+json" } }
      );
      if (!resp.ok) throw new Error(`GitHub API: ${resp.status}`);
      const items: GithubContent[] = await resp.json();

      const skillDirs = items.filter((item) => item.type === "dir");
      const remote: RemoteSkill[] = [];

      // Fetch SKILL.md for each directory to get descriptions
      const promises = skillDirs.map(async (dir) => {
        try {
          const skillMdUrl = `https://raw.githubusercontent.com/${ANTHROPIC_REPO}/main/${dir.path}/SKILL.md`;
          const mdResp = await fetch(skillMdUrl);
          if (!mdResp.ok) return null;
          const mdText = await mdResp.text();

          // Parse YAML frontmatter description
          let description = "";
          if (mdText.startsWith("---")) {
            const parts = mdText.split("---");
            if (parts.length >= 3) {
              const frontmatter = parts[1];
              const descMatch = frontmatter.match(/description:\s*["']?(.+?)["']?\s*$/m);
              if (descMatch) description = descMatch[1].trim();
            }
          }

          return {
            name: dir.name,
            description: description || `Skill from ${ANTHROPIC_REPO}`,
            source: "anthropic" as const,
            repoUrl: `https://github.com/${ANTHROPIC_REPO}/tree/main/${dir.path}`,
            downloadUrl: dir.path,
          };
        } catch {
          return null;
        }
      });

      const results = await Promise.all(promises);
      results.forEach((r) => { if (r) remote.push(r); });

      setSkills(remote);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch skills");
    } finally {
      setLoading(false);
    }
  };

  const handleInstall = async (skill: RemoteSkill) => {
    if (installing) return;
    setInstalling(skill.name);

    try {
      // Fetch all files in the skill directory
      const resp = await fetch(
        `https://api.github.com/repos/${ANTHROPIC_REPO}/contents/${skill.downloadUrl}`,
        { headers: { Accept: "application/vnd.github.v3+json" } }
      );
      if (!resp.ok) throw new Error(`Failed to list files: ${resp.status}`);
      const items: GithubContent[] = await resp.json();

      // Download and save each file
      for (const item of items) {
        if (item.type === "file" && item.download_url) {
          const fileResp = await fetch(item.download_url);
          if (!fileResp.ok) continue;
          const content = await fileResp.text();
          await saveFile(`skills/${skill.name}/${item.name}`, content);
        } else if (item.type === "dir") {
          // Recursively fetch subdirectory files
          await installDir(`${skill.downloadUrl}/${item.name}`, `skills/${skill.name}/${item.name}`);
        }
      }

      setInstalled((prev) => new Set(prev).add(skill.name));
    } catch {
      // Installation error handled silently
    } finally {
      setInstalling(null);
    }
  };

  const installDir = async (remotePath: string, localPrefix: string) => {
    try {
      const resp = await fetch(
        `https://api.github.com/repos/${ANTHROPIC_REPO}/contents/${remotePath}`,
        { headers: { Accept: "application/vnd.github.v3+json" } }
      );
      if (!resp.ok) return;
      const items: GithubContent[] = await resp.json();

      for (const item of items) {
        if (item.type === "file" && item.download_url) {
          const fileResp = await fetch(item.download_url);
          if (!fileResp.ok) continue;
          const content = await fileResp.text();
          await saveFile(`${localPrefix}/${item.name}`, content);
        } else if (item.type === "dir") {
          await installDir(`${remotePath}/${item.name}`, `${localPrefix}/${item.name}`);
        }
      }
    } catch {
      // Skip failed subdirectories
    }
  };

  const filtered = skills.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.description.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 animate-fade-in" style={{ background: "rgba(0,0,0,0.5)" }}>
      <div className="w-[700px] max-h-[80vh] rounded-xl shadow-2xl overflow-hidden flex flex-col" style={{ background: "var(--bg-surface)" }}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2">
            <Globe className="w-5 h-5" style={{ color: "var(--accent)" }} />
            <span className="text-[16px] font-semibold" style={{ color: "var(--text-primary)" }}>
              技能商店
            </span>
            <span className="text-[11px] px-2 py-0.5 rounded-full" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
              Anthropic Skills
            </span>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-md transition-colors hover:opacity-80" style={{ color: "var(--text-muted)" }}>
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search */}
        <div className="px-6 py-3 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5" style={{ color: "var(--text-muted)" }} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索公开技能..."
              className="w-full pl-9 pr-3 py-2 rounded-lg text-[12px] outline-none transition-all"
              style={{ background: "var(--bg-page)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--accent)" }} />
              <p className="text-[12px]" style={{ color: "var(--text-muted)" }}>
                正在从 GitHub 加载技能列表...
              </p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <AlertCircle className="w-6 h-6" style={{ color: "var(--text-muted)" }} />
              <p className="text-[12px]" style={{ color: "var(--text-muted)" }}>{error}</p>
              <button
                onClick={fetchSkills}
                className="px-4 py-1.5 text-[12px] rounded-lg transition-colors"
                style={{ border: "1px solid var(--border)", color: "var(--text-secondary)" }}
              >
                重试
              </button>
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 gap-2">
              <p className="text-[12px]" style={{ color: "var(--text-muted)" }}>
                {search ? "没有找到匹配的技能" : "暂无可用技能"}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filtered.map((skill) => {
                const isInstalled = installed.has(skill.name);
                const isInstalling = installing === skill.name;

                return (
                  <div
                    key={skill.name}
                    className="rounded-xl p-4 transition-all shadow-sm hover:shadow-md"
                    style={{ border: `1px solid ${isInstalled ? "var(--accent)" : "var(--border)"}`, background: "var(--bg-surface)" }}
                  >
                    <div className="flex items-start gap-3">
                      {/* Icon */}
                      <div
                        className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 text-[16px] font-bold"
                        style={{ background: "var(--accent-bg)", color: "var(--accent)" }}
                      >
                        {skill.name.charAt(0).toUpperCase()}
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
                            {skill.name}
                          </span>
                          <span className="text-[9px] px-1.5 py-0.5 rounded-full font-medium" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
                            {skill.source === "anthropic" ? "Anthropic" : "Community"}
                          </span>
                        </div>
                        <p className="text-[11px] leading-relaxed mb-2" style={{ color: "var(--text-muted)" }}>
                          {skill.description.length > 150 ? skill.description.slice(0, 150) + "..." : skill.description}
                        </p>
                        <a
                          href={skill.repoUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[10px] transition-colors hover:opacity-80"
                          style={{ color: "var(--accent)" }}
                        >
                          GitHub <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      </div>

                      {/* Install button */}
                      <button
                        onClick={() => !isInstalled && handleInstall(skill)}
                        disabled={isInstalling || isInstalled}
                        className="px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all disabled:opacity-60 flex items-center gap-1.5 shrink-0"
                        style={{
                          background: isInstalled ? "var(--accent-bg)" : "var(--accent)",
                          color: isInstalled ? "var(--accent)" : "white",
                        }}
                      >
                        {isInstalling ? (
                          <>
                            <Loader2 className="w-3 h-3 animate-spin" />
                            安装中
                          </>
                        ) : isInstalled ? (
                          <>
                            <CheckCircle2 className="w-3 h-3" />
                            已安装
                          </>
                        ) : (
                          <>
                            <Download className="w-3 h-3" />
                            安装
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3 shrink-0" style={{ borderTop: "1px solid var(--border)", background: "var(--bg-page)" }}>
          <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
            {skills.length} 个可用技能 {installed.size > 0 && `· ${installed.size} 个已安装`}
          </span>
          <div className="flex items-center gap-2">
            {installed.size > 0 && (
              <button
                onClick={() => { onInstalled(); onClose(); }}
                className="px-4 py-1.5 text-[12px] font-medium text-white rounded-lg transition-all"
                style={{ background: "var(--accent)" }}
              >
                刷新技能列表
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-1.5 text-[12px] font-medium rounded-lg"
              style={{ color: "var(--text-secondary)", border: "1px solid var(--border)" }}
            >
              关闭
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
