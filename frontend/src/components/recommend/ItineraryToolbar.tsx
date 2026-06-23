"use client";

import { AlertTriangle, Loader2, Route, X } from "lucide-react";
import { useApp } from "@/lib/store";
import {
  MAX_ITINERARY_STOPS,
  MIN_ITINERARY_STOPS,
  type TransportMode,
} from "@/lib/recommend-types";

const TRANSPORT_OPTIONS: { value: TransportMode; label: string }[] = [
  { value: "walking", label: "步行" },
  { value: "driving", label: "驾车" },
  { value: "transit", label: "公交" },
];

export default function ItineraryToolbar() {
  const {
    selectedPoiIds,
    transportMode,
    setTransportMode,
    clearSelectedPois,
    isBuildingItinerary,
    isRecommending,
    lastItineraryError,
    buildWeekendItinerary,
    currentFeed,
  } = useApp();

  const hasFeed = (currentFeed?.items.length ?? 0) > 0;
  if (!hasFeed) return null;

  const selectedCount = selectedPoiIds.length;
  const canBuild =
    selectedCount >= MIN_ITINERARY_STOPS &&
    !isBuildingItinerary &&
    !isRecommending;
  const atMax = selectedCount >= MAX_ITINERARY_STOPS;

  return (
    <div
      className="shrink-0 px-4 py-3 space-y-2"
      style={{
        borderTop: "1px solid var(--border)",
        background: "var(--bg-surface)",
      }}
    >
      {lastItineraryError && (
        <div
          className="flex items-start gap-2 px-3 py-2 rounded-lg text-[12px]"
          style={{
            background: "rgba(239, 68, 68, 0.08)",
            border: "1px solid rgba(239, 68, 68, 0.25)",
            color: "var(--text-secondary)",
          }}
        >
          <AlertTriangle className="w-4 h-4 shrink-0 text-red-500 mt-0.5" />
          <span>{lastItineraryError.message}</span>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <Route className="w-4 h-4 shrink-0" style={{ color: "var(--accent)" }} />
          <span className="text-[12px]" style={{ color: "var(--text-secondary)" }}>
            已选{" "}
            <strong style={{ color: "var(--text-primary)" }}>{selectedCount}</strong>
            /{MAX_ITINERARY_STOPS} 个站点
            {selectedCount > 0 && selectedCount < MIN_ITINERARY_STOPS && (
              <span style={{ color: "var(--text-muted)" }}>
                {" "}
                · 至少选 {MIN_ITINERARY_STOPS} 个
              </span>
            )}
            {atMax && (
              <span style={{ color: "var(--text-muted)" }}> · 已达上限</span>
            )}
          </span>
          {selectedCount > 0 && (
            <button
              type="button"
              onClick={clearSelectedPois}
              disabled={isBuildingItinerary}
              className="inline-flex items-center gap-0.5 text-[11px] px-1.5 py-0.5 rounded transition-opacity hover:opacity-80 disabled:opacity-50"
              style={{ color: "var(--text-muted)" }}
            >
              <X className="w-3 h-3" />
              清空
            </button>
          )}
        </div>

        <select
          value={transportMode}
          onChange={(e) => setTransportMode(e.target.value as TransportMode)}
          disabled={isBuildingItinerary || isRecommending}
          className="text-[12px] px-2.5 py-1.5 rounded-lg outline-none disabled:opacity-50"
          style={{
            color: "var(--text-secondary)",
            background: "var(--bg-page)",
            border: "1px solid var(--border)",
          }}
          aria-label="交通方式"
        >
          {TRANSPORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <button
          type="button"
          onClick={() => void buildWeekendItinerary()}
          disabled={!canBuild}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
          style={{
            background: "var(--accent)",
            color: "#fff",
          }}
        >
          {isBuildingItinerary ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Route className="w-3.5 h-3.5" />
          )}
          生成周末行程
        </button>
      </div>
    </div>
  );
}
