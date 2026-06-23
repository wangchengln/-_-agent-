"use client";

import { CloudRain, CloudSun, Info } from "lucide-react";
import type { WeatherSnapshot } from "@/lib/recommend-types";

interface Props {
  weather: WeatherSnapshot | null | undefined;
  /** Prefer feed weather; itinerary weather as fallback when planning. */
  className?: string;
}

export default function WeatherBanner({ weather, className = "" }: Props) {
  if (!weather?.fetched) return null;

  const isRainy = weather.is_rainy;
  const cityLabel = weather.city ? `${weather.city}` : "当前区域";
  const tempLabel =
    weather.temperature != null && weather.temperature !== ""
      ? `${weather.temperature}°C`
      : null;
  const summaryParts = [weather.summary, tempLabel].filter(Boolean);
  const summaryText = summaryParts.join(" · ");

  return (
    <div
      className={`flex items-start gap-2.5 px-3 py-2.5 rounded-xl text-[12px] leading-relaxed ${className}`}
      style={{
        background: isRainy ? "rgba(59, 130, 246, 0.1)" : "rgba(14, 165, 233, 0.08)",
        border: isRainy
          ? "1px solid rgba(59, 130, 246, 0.35)"
          : "1px solid rgba(14, 165, 233, 0.25)",
        color: "var(--text-secondary)",
      }}
    >
      {isRainy ? (
        <CloudRain className="w-4 h-4 shrink-0 text-blue-500 mt-0.5" />
      ) : (
        <CloudSun className="w-4 h-4 shrink-0 text-sky-500 mt-0.5" />
      )}
      <div className="min-w-0 space-y-0.5">
        <p className="font-medium" style={{ color: "var(--text-primary)" }}>
          {cityLabel}
          {summaryText ? ` · ${summaryText}` : ""}
        </p>
        {isRainy && weather.injected_rule ? (
          <p className="flex items-start gap-1 text-[11px]">
            <Info className="w-3 h-3 shrink-0 mt-0.5 opacity-70" />
            <span>{weather.injected_rule}</span>
          </p>
        ) : (
          <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>
            {isRainy
              ? "天气可能影响户外体验，推荐结果已考虑室内优先。"
              : "天气良好，适合安排室内外活动。"}
          </p>
        )}
      </div>
    </div>
  );
}
