"use client";

import { useState, useEffect } from "react";
import { X, Eye, EyeOff, Save, Shield } from "lucide-react";
import { getApiKeys, setApiKeys } from "@/lib/api";

interface Props {
  onClose: () => void;
}

interface KeyField {
  key: string;
  label: string;
  isUrl: boolean;
  hint?: string;
}

const KEY_FIELDS: KeyField[] = [
  { key: "DEEPSEEK_API_KEY", label: "DeepSeek API Key", isUrl: false },
  { key: "OPENAI_API_KEY", label: "OpenAI API Key", isUrl: false },
  { key: "OPENAI_BASE_URL", label: "OpenAI Base URL", isUrl: true },
  { key: "TAVILY_API_KEY", label: "Tavily API Key", isUrl: false },
  {
    key: "AMAP_WEB_SERVICE_KEY",
    label: "高德 Web 服务 Key",
    isUrl: false,
    hint: "后端 POI / 天气 / 路径（非 JS Key）",
  },
];

export default function SettingsModal({ onClose }: Props) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [originalValues, setOriginalValues] = useState<Record<string, string>>({});
  const [visible, setVisible] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getApiKeys()
      .then((keys) => {
        setValues(keys);
        setOriginalValues(keys);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      // Only send changed fields
      const changed: Record<string, string> = {};
      for (const { key } of KEY_FIELDS) {
        if (values[key] !== originalValues[key]) {
          changed[key] = values[key] || "";
        }
      }
      if (Object.keys(changed).length === 0) {
        onClose();
        return;
      }
      const result = await setApiKeys(changed);
      setValues(result);
      setOriginalValues(result);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center" style={{ background: "rgba(0,0,0,0.5)" }}>
      <div
        className="w-[480px] max-w-[90vw] rounded-2xl shadow-2xl animate-fade-in-scale"
        style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: "1px solid var(--border)" }}>
          <h2 className="text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>
            Settings
          </h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:opacity-80" style={{ color: "var(--text-muted)" }}>
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          {loading ? (
            <p className="text-[13px] text-center py-8" style={{ color: "var(--text-muted)" }}>Loading...</p>
          ) : (
            KEY_FIELDS.map(({ key, label, isUrl, hint }) => (
              <div key={key}>
                <label className="block text-[12px] font-medium mb-1.5" style={{ color: "var(--text-secondary)" }}>
                  {label}
                </label>
                {hint && (
                  <p className="text-[10px] mb-1" style={{ color: "var(--text-muted)" }}>
                    {hint}
                  </p>
                )}
                <div className="relative">
                  <input
                    type={isUrl || visible[key] ? "text" : "password"}
                    className="w-full px-3 py-2 pr-10 text-[13px] rounded-lg border outline-none transition-colors focus:ring-1"
                    style={{
                      background: "var(--bg-page)",
                      borderColor: "var(--border)",
                      color: "var(--text-primary)",
                    }}
                    value={values[key] || ""}
                    onChange={(e) => setValues((prev) => ({ ...prev, [key]: e.target.value }))}
                    placeholder={isUrl ? "https://..." : "Enter API key"}
                  />
                  {!isUrl && (
                    <button
                      onClick={() => setVisible((prev) => ({ ...prev, [key]: !prev[key] }))}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded hover:opacity-80"
                      style={{ color: "var(--text-muted)" }}
                      type="button"
                    >
                      {visible[key] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  )}
                </div>
              </div>
            ))
          )}

          {/* Security note */}
          <div className="flex items-start gap-2 pt-2">
            <Shield className="w-3.5 h-3.5 shrink-0 mt-0.5" style={{ color: "var(--text-muted)" }} />
            <p className="text-[11px] leading-relaxed" style={{ color: "var(--text-muted)" }}>
              API Key 安全存储在本地 .env 文件中，不会上传到任何服务器。
              高德 JS API Key 请配置在 frontend/.env.local（NEXT_PUBLIC_AMAP_JS_KEY）。
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4" style={{ borderTop: "1px solid var(--border)" }}>
          <button
            onClick={onClose}
            className="px-4 py-2 text-[13px] rounded-lg transition-colors hover:opacity-80"
            style={{ color: "var(--text-secondary)", border: "1px solid var(--border)" }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 text-[13px] font-medium rounded-lg text-white transition-colors hover:opacity-90 disabled:opacity-50"
            style={{ background: "var(--accent)" }}
          >
            <Save className="w-3.5 h-3.5" />
            {saved ? "Saved!" : saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
