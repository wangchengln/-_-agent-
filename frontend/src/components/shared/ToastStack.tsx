"use client";

import { useEffect } from "react";
import { CheckCircle2, Info, X, AlertTriangle } from "lucide-react";
import { useApp, type ToastItem } from "@/lib/store";

function ToastIcon({ tone }: { tone: ToastItem["tone"] }) {
  if (tone === "success") {
    return <CheckCircle2 className="w-4 h-4 shrink-0 text-green-600" />;
  }
  if (tone === "warning") {
    return <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600" />;
  }
  return <Info className="w-4 h-4 shrink-0" style={{ color: "var(--accent)" }} />;
}

export default function ToastStack() {
  const { toasts, dismissToast } = useApp();

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-[200] flex flex-col gap-2 max-w-sm pointer-events-none"
      aria-live="polite"
    >
      {toasts.map((toast) => (
        <ToastRow key={toast.id} toast={toast} onDismiss={() => dismissToast(toast.id)} />
      ))}
    </div>
  );
}

function ToastRow({
  toast,
  onDismiss,
}: {
  toast: ToastItem;
  onDismiss: () => void;
}) {
  useEffect(() => {
    const timer = window.setTimeout(onDismiss, toast.durationMs ?? 3200);
    return () => window.clearTimeout(timer);
  }, [onDismiss, toast.durationMs]);

  return (
    <div
      className="pointer-events-auto flex items-start gap-2.5 px-3.5 py-2.5 rounded-xl shadow-lg animate-toast-in"
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        color: "var(--text-secondary)",
      }}
    >
      <ToastIcon tone={toast.tone} />
      <p className="text-[12px] leading-relaxed flex-1 pt-0.5">{toast.message}</p>
      <button
        type="button"
        onClick={onDismiss}
        className="p-0.5 rounded transition-opacity hover:opacity-70 shrink-0"
        style={{ color: "var(--text-muted)" }}
        aria-label="关闭提示"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
