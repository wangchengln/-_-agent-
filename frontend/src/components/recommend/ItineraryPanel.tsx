"use client";

import {
  AlertTriangle,
  ArrowDown,
  Clock,
  Copy,
  MapPin,
  MonitorPlay,
  Route,
  X,
} from "lucide-react";
import { useApp } from "@/lib/store";
import { copyItineraryToClipboard } from "@/lib/itinerary-text";
import {
  formatDurationMinutes,
  formatMeters,
  formatTransportMode,
  type ItineraryLeg,
  type ItineraryStop,
} from "@/lib/recommend-types";
import WeatherBanner from "./WeatherBanner";
import AmapMap from "./AmapMap";

interface Props {
  onClose: () => void;
  onOpenCanvas?: () => void;
}

function LegRow({ leg }: { leg: ItineraryLeg }) {
  const durationMin = Math.max(1, Math.round(leg.duration_s / 60));
  return (
    <div className="flex gap-3 py-2 pl-1">
      <div className="flex flex-col items-center w-5 shrink-0 pt-1">
        <div
          className="w-2 h-2 rounded-full border-2"
          style={{ borderColor: "var(--border)", background: "var(--bg-page)" }}
        />
        <div className="w-px flex-1 min-h-[24px]" style={{ background: "var(--border)" }} />
      </div>
      <div
        className="flex-1 rounded-lg px-3 py-2 text-[11px] mb-1"
        style={{
          background: "var(--bg-page)",
          border: "1px dashed var(--border)",
          color: "var(--text-muted)",
        }}
      >
        <div className="flex items-center gap-1.5 font-medium" style={{ color: "var(--text-secondary)" }}>
          <Route className="w-3 h-3 shrink-0" style={{ color: "var(--accent)" }} />
          {formatTransportMode(leg.mode)}
          {leg.estimated && (
            <span className="text-[10px] px-1 rounded" style={{ background: "var(--accent-bg)" }}>
              估算
            </span>
          )}
        </div>
        <p className="mt-0.5">
          {leg.depart_at} → {leg.arrive_at} · {durationMin} 分钟 · {formatMeters(leg.distance_m)}
        </p>
      </div>
    </div>
  );
}

function StopRow({
  stop,
  active,
  onSelect,
}: {
  stop: ItineraryStop;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="w-full text-left flex gap-3 py-1 group"
    >
      <div className="flex flex-col items-center w-5 shrink-0">
        <div
          className="w-3 h-3 rounded-full shrink-0 transition-colors"
          style={{
            background: active ? "var(--accent)" : "var(--accent-bg)",
            border: active ? "none" : "2px solid var(--accent)",
          }}
        />
        <div className="w-px flex-1 min-h-[48px]" style={{ background: "var(--border)" }} />
      </div>
      <div
        className="flex-1 rounded-xl px-3 py-2.5 mb-2 transition-colors"
        style={{
          background: active ? "var(--accent-bg)" : "var(--bg-surface)",
          border: active ? "1px solid var(--border-accent)" : "1px solid var(--border)",
        }}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-[10px] font-medium mb-0.5" style={{ color: "var(--accent)" }}>
              第 {stop.order} 站
            </p>
            <h4
              className="text-[13px] font-semibold leading-snug truncate"
              style={{ color: "var(--text-primary)" }}
            >
              {stop.name}
            </h4>
            <p className="text-[10px] truncate mt-0.5" style={{ color: "var(--text-muted)" }}>
              {stop.type.replace(/;/g, " · ")}
            </p>
          </div>
          <div
            className="shrink-0 text-right text-[11px] font-mono"
            style={{ color: "var(--text-secondary)" }}
          >
            <div className="flex items-center gap-1 justify-end">
              <Clock className="w-3 h-3 opacity-60" />
              {stop.arrive_at}–{stop.leave_at}
            </div>
            <p className="text-[10px] mt-0.5" style={{ color: "var(--text-muted)" }}>
              停留 {stop.dwell_min} 分钟
            </p>
          </div>
        </div>
        {stop.address && (
          <p className="text-[10px] mt-1.5 flex items-center gap-1 truncate" style={{ color: "var(--text-muted)" }}>
            <MapPin className="w-3 h-3 shrink-0" />
            {stop.address}
          </p>
        )}
      </div>
    </button>
  );
}

export default function ItineraryPanel({ onClose, onOpenCanvas }: Props) {
  const {
    currentItinerary,
    activeItineraryStopId,
    setActiveItineraryStopId,
    pushToast,
  } = useApp();

  if (!currentItinerary) {
    return (
      <div className="flex flex-col h-full" style={{ background: "var(--bg-surface)" }}>
        <Header onClose={onClose} />
        <div className="flex-1 flex items-center justify-center px-6 text-center">
          <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>
            从推荐 feed 选择 2–5 个地点后，点击「生成周末行程」查看时间线
          </p>
        </div>
      </div>
    );
  }

  const { stops, legs, warnings } = currentItinerary;
  const legByToId = new Map(legs.map((leg) => [leg.to_poi_id, leg]));

  return (
    <div className="flex flex-col h-full" style={{ background: "var(--bg-surface)" }}>
      <Header
        onClose={onClose}
        onOpenCanvas={onOpenCanvas}
        onCopy={async () => {
          const ok = await copyItineraryToClipboard(currentItinerary);
          pushToast(
            ok ? "行程文本已复制到剪贴板" : "复制失败，请手动选择复制",
            { tone: ok ? "success" : "warning" }
          );
        }}
      />

      <div className="px-4 pt-3 shrink-0">
        <AmapMap
          className="h-[220px] w-full"
          stops={stops}
          legs={legs}
          activeStopId={activeItineraryStopId}
          onStopSelect={(poiId) => setActiveItineraryStopId(poiId)}
        />
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        <WeatherBanner weather={currentItinerary.weather} />

        {warnings.length > 0 && (
          <div
            className="flex items-start gap-2 px-3 py-2 rounded-lg text-[11px]"
            style={{
              background: "rgba(234, 179, 8, 0.12)",
              border: "1px solid rgba(234, 179, 8, 0.35)",
              color: "var(--text-secondary)",
            }}
          >
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-500 mt-0.5" />
            <ul className="space-y-0.5">
              {warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        <div
          className="rounded-xl px-3 py-2 text-[11px] flex flex-wrap gap-x-3 gap-y-1"
          style={{
            background: "var(--bg-page)",
            border: "1px solid var(--border)",
            color: "var(--text-muted)",
          }}
        >
          <span>
            {formatTransportMode(currentItinerary.transport_mode)} ·{" "}
            {currentItinerary.day_start}–{currentItinerary.day_end}
          </span>
          <span>停留 {formatDurationMinutes(currentItinerary.total_dwell_min)}</span>
          <span>通勤 {formatDurationMinutes(currentItinerary.total_travel_min)}</span>
          <span>路程 {formatMeters(currentItinerary.total_distance_m)}</span>
        </div>

        <div>
          {stops.map((stop, index) => {
            const leg = legByToId.get(stop.poi_id);
            const showLeg = index > 0 && leg;
            return (
              <div key={stop.poi_id}>
                {showLeg && leg && <LegRow leg={leg} />}
                {!showLeg && index > 0 && (
                  <div className="flex justify-center py-1 opacity-40">
                    <ArrowDown className="w-4 h-4" />
                  </div>
                )}
                <StopRow
                  stop={stop}
                  active={activeItineraryStopId === stop.poi_id}
                  onSelect={() =>
                    setActiveItineraryStopId(
                      activeItineraryStopId === stop.poi_id ? null : stop.poi_id
                    )
                  }
                />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Header({
  onClose,
  onOpenCanvas,
  onCopy,
}: {
  onClose: () => void;
  onOpenCanvas?: () => void;
  onCopy?: () => void;
}) {
  return (
    <div
      className="h-14 flex items-center justify-between px-4 shrink-0 gap-2"
      style={{ borderBottom: "1px solid var(--border)" }}
    >
      <div className="flex items-center gap-2 min-w-0">
        <Route className="w-4 h-4 shrink-0" style={{ color: "var(--accent)" }} />
        <span className="text-[14px] font-semibold truncate" style={{ color: "var(--text-primary)" }}>
          周末行程
        </span>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        {onCopy && (
          <button
            type="button"
            onClick={onCopy}
            className="p-1.5 rounded-lg transition-opacity hover:opacity-70"
            style={{ color: "var(--text-muted)" }}
            title="复制行程文本"
            aria-label="复制行程"
          >
            <Copy className="w-4 h-4" />
          </button>
        )}
        {onOpenCanvas && (
          <button
            type="button"
            onClick={onOpenCanvas}
            className="p-1.5 rounded-lg transition-opacity hover:opacity-70"
            style={{ color: "var(--accent)" }}
            title="在 Canvas 查看时间轴"
            aria-label="打开 Canvas"
          >
            <MonitorPlay className="w-4 h-4" />
          </button>
        )}
        <button
          type="button"
          onClick={onClose}
          className="p-1.5 rounded-lg transition-opacity hover:opacity-70"
          style={{ color: "var(--text-muted)" }}
          aria-label="关闭行程面板"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
