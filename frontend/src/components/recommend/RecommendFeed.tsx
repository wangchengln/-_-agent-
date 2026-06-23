"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Loader2,
  MapPin,
  PanelRightOpen,
  Route,
  Sparkles,
} from "lucide-react";
import { useApp } from "@/lib/store";
import { RECOMMEND_ERROR_SUGGESTIONS, MAX_ITINERARY_STOPS, type FeedItem } from "@/lib/recommend-types";
import { REFINEMENT_CHIPS, buildDislikeCommand } from "@/lib/weekend-bridge";
import ThoughtChain from "@/components/chat/ThoughtChain";
import RecommendCard from "./RecommendCard";
import CardCarousel from "./CardCarousel";
import PoiDetailSheet from "./PoiDetailSheet";
import FeedMapOverview from "./FeedMapOverview";
import RecommendInput from "./RecommendInput";
import ItineraryToolbar from "./ItineraryToolbar";
import WeatherBanner from "./WeatherBanner";

const QUICK_HINTS = [
  "上海周末文艺一点，别去商场，不要太远",
  "徐汇区附近适合拍照的咖啡馆",
  "想要室外亲子活动，人均别太高",
];

interface Props {
  onOpenPreference?: () => void;
  onOpenItinerary?: () => void;
  /** Compact header when embedded in weekend dual-column layout */
  embedded?: boolean;
}

function FeedSkeleton() {
  return (
    <div className="flex justify-center py-4">
      <div
        className="w-[88%] max-w-[420px] rounded-xl overflow-hidden animate-pulse"
        style={{ border: "1px solid var(--border)", background: "var(--bg-surface)" }}
      >
        <div className="aspect-[16/10] shimmer-bg" style={{ background: "var(--accent-bg)" }} />
        <div className="p-4 space-y-3">
          <div className="h-4 rounded" style={{ background: "var(--accent-bg)", width: "70%" }} />
          <div className="h-3 rounded" style={{ background: "var(--accent-bg)", width: "45%" }} />
          <div className="h-3 rounded" style={{ background: "var(--accent-bg)", width: "90%" }} />
        </div>
      </div>
    </div>
  );
}

function QuickHint({ text }: { text: string }) {
  const { sendRecommendCommand, isRecommending } = useApp();
  return (
    <button
      onClick={() => !isRecommending && sendRecommendCommand(text)}
      disabled={isRecommending}
      className="px-3 py-1.5 rounded-full text-[12px] transition-all shadow-sm hover:shadow-md disabled:opacity-50 text-left"
      style={{
        color: "var(--text-secondary)",
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
      }}
    >
      {text}
    </button>
  );
}

function RefinementChips({
  activeItem,
  disabled,
}: {
  activeItem: FeedItem | null;
  disabled: boolean;
}) {
  const { sendRecommendCommand } = useApp();

  return (
    <div className="shrink-0 px-2 pb-2 space-y-2">
      <p className="text-[10px] text-center" style={{ color: "var(--text-muted)" }}>
        快捷微调 · 同步更新推荐
      </p>
      <div className="flex flex-wrap gap-1.5 justify-center max-w-lg mx-auto">
        {REFINEMENT_CHIPS.map((chip) => (
          <button
            key={chip.label}
            type="button"
            disabled={disabled}
            onClick={() => sendRecommendCommand(chip.command)}
            className="px-2.5 py-1 rounded-full text-[11px] transition-opacity hover:opacity-80 disabled:opacity-40"
            style={{
              background: "var(--bg-surface)",
              color: "var(--text-secondary)",
              border: "1px solid var(--border)",
            }}
          >
            {chip.label}
          </button>
        ))}
        {activeItem && (
          <button
            type="button"
            disabled={disabled}
            onClick={() => sendRecommendCommand(buildDislikeCommand(activeItem.name))}
            className="px-2.5 py-1 rounded-full text-[11px] transition-opacity hover:opacity-80 disabled:opacity-40"
            style={{
              background: "rgba(239, 68, 68, 0.08)",
              color: "#dc2626",
              border: "1px solid rgba(239, 68, 68, 0.25)",
            }}
          >
            不喜欢「{activeItem.name.slice(0, 8)}
            {activeItem.name.length > 8 ? "…" : ""}」
          </button>
        )}
      </div>
    </div>
  );
}

export default function RecommendFeed({ onOpenPreference, onOpenItinerary, embedded = false }: Props) {
  const {
    currentFeed,
    round,
    sessionId,
    preference,
    intentSummary,
    needsClarification,
    isRecommending,
    recommendToolCalls,
    recommendRationale,
    lastRecommendError,
    sendRecommendCommand,
    selectedPoiIds,
    toggleSelectPoi,
    currentItinerary,
  } = useApp();

  const [rationaleOpen, setRationaleOpen] = useState(false);
  const [detailItem, setDetailItem] = useState<FeedItem | null>(null);
  const [activeCardIndex, setActiveCardIndex] = useState(0);
  const bodyRef = useRef<HTMLDivElement>(null);

  const items = currentFeed?.items ?? [];
  const showSkeleton = isRecommending && items.length === 0;
  const showEmpty = !isRecommending && items.length === 0 && !lastRecommendError;
  const dimCards = isRecommending && items.length > 0;
  const anchor = preference?.anchor ?? currentFeed?.preference.anchor ?? null;
  const selectionAtMax = selectedPoiIds.length >= MAX_ITINERARY_STOPS;

  useEffect(() => {
    setDetailItem(null);
    setActiveCardIndex(0);
  }, [round, sessionId]);

  useEffect(() => {
    if (round > 0) {
      bodyRef.current?.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [round]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div
        className={`${embedded ? "h-12 px-4" : "h-14 px-6"} flex items-center justify-between shrink-0`}
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={`${embedded ? "w-7 h-7" : "w-8 h-8"} rounded-lg flex items-center justify-center shrink-0`}
            style={{ background: "var(--accent-bg)" }}
          >
            <MapPin className={`${embedded ? "w-3.5 h-3.5" : "w-4 h-4"}`} style={{ color: "var(--accent)" }} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span
                className={`${embedded ? "text-[13px]" : "text-[14px]"} font-semibold`}
                style={{ color: "var(--text-primary)" }}
              >
                {embedded ? "出行推荐" : "周末出行推荐"}
              </span>
              {round > 0 && (
                <span
                  className="text-[10px] px-2 py-0.5 rounded-full shrink-0"
                  style={{ background: "var(--accent-bg)", color: "var(--accent)" }}
                >
                  第 {round} 轮
                  {items.length > 0 ? ` · ${items.length} 个结果` : ""}
                </span>
              )}
              {isRecommending && (
                <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" style={{ color: "var(--accent)" }} />
              )}
            </div>
            {intentSummary ? (
              <p
                className="text-[11px] truncate flex items-center gap-1"
                style={{ color: needsClarification ? "#d97706" : "var(--text-muted)" }}
              >
                {needsClarification && (
                  <AlertTriangle className="w-3 h-3 shrink-0 text-amber-500" />
                )}
                {intentSummary}
              </p>
            ) : (
              <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>
                {embedded
                  ? "自然语言微调偏好，结果实时更新"
                  : "用自然语言描述偏好，实时调控推荐结果"}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {items.length > 0 && currentFeed?.total_candidates != null && (
            <span className="text-[10px] hidden sm:inline" style={{ color: "var(--text-muted)" }}>
              {items.length} / {currentFeed.total_candidates} 候选
            </span>
          )}
          {selectedPoiIds.length > 0 && (
            <span
              className="text-[10px] px-2 py-0.5 rounded-full shrink-0"
              style={{ background: "var(--accent-bg)", color: "var(--accent)" }}
            >
              已选 {selectedPoiIds.length}
            </span>
          )}
          {onOpenPreference && (
            <button
              onClick={onOpenPreference}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-colors hover:opacity-80"
              style={{
                color: "var(--text-secondary)",
                border: "1px solid var(--border)",
                background: "var(--bg-surface)",
              }}
              title="查看当前偏好"
            >
              <PanelRightOpen className="w-3.5 h-3.5" />
              偏好
            </button>
          )}
          {currentItinerary && onOpenItinerary && (
            <button
              onClick={onOpenItinerary}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-colors hover:opacity-80"
              style={{
                color: "var(--accent)",
                border: "1px solid var(--border-accent)",
                background: "var(--accent-bg)",
              }}
              title="查看周末行程"
            >
              <Route className="w-3.5 h-3.5" />
              行程
            </button>
          )}
        </div>
      </div>

      {/* Scrollable body */}
      <div ref={bodyRef} className="flex-1 overflow-y-auto min-h-0 flex flex-col">
        <div className={`${embedded ? "px-4 py-4" : "max-w-5xl mx-auto px-6 py-5"} space-y-4 shrink-0`}>
          <WeatherBanner weather={currentFeed?.weather} />

          {needsClarification && (
            <div
              className="flex items-start gap-2 px-3 py-2 rounded-lg text-[12px]"
              style={{
                background: "rgba(234, 179, 8, 0.12)",
                border: "1px solid rgba(234, 179, 8, 0.35)",
                color: "var(--text-secondary)",
              }}
            >
              <AlertTriangle className="w-4 h-4 shrink-0 text-amber-500 mt-0.5" />
              <span>理解可能不够准确，若结果不符请补充说明地点或偏好。</span>
            </div>
          )}

          {lastRecommendError && (
            <div
              className="rounded-xl px-4 py-3 space-y-2.5"
              style={{
                background: "rgba(239, 68, 68, 0.08)",
                border: "1px solid rgba(239, 68, 68, 0.25)",
              }}
            >
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-500 mt-0.5" />
                <div className="space-y-0.5">
                  <p className="text-[13px] font-medium" style={{ color: "var(--text-primary)" }}>
                    {lastRecommendError.message}
                  </p>
                  {lastRecommendError.retry_hint && (
                    <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>
                      {lastRecommendError.retry_hint}
                    </p>
                  )}
                </div>
              </div>
              {items.length > 0 && (
                <p className="text-[10px] pl-6" style={{ color: "var(--text-muted)" }}>
                  已保留上一轮推荐结果
                </p>
              )}
              {RECOMMEND_ERROR_SUGGESTIONS[lastRecommendError.code].length > 0 && (
                <div className="flex flex-wrap gap-1.5 pl-6">
                  {RECOMMEND_ERROR_SUGGESTIONS[lastRecommendError.code].map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => !isRecommending && sendRecommendCommand(suggestion)}
                      disabled={isRecommending}
                      className="text-[11px] px-2.5 py-1 rounded-full transition-opacity hover:opacity-80 disabled:opacity-50"
                      style={{
                        background: "var(--bg-surface)",
                        color: "var(--accent)",
                        border: "1px solid var(--border-accent)",
                      }}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {showEmpty && (
            <div className="flex flex-col items-center justify-center py-16">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4 shadow-lg"
                style={{ background: "var(--accent)" }}
              >
                <Sparkles className="w-7 h-7 text-white" />
              </div>
              <h2 className="text-lg font-semibold mb-1" style={{ color: "var(--text-primary)" }}>
                规划你的周末出行
              </h2>
              <p
                className="text-[13px] max-w-md text-center leading-relaxed mb-5"
                style={{ color: "var(--text-muted)" }}
              >
                告诉我城市、氛围和约束，我会用 IRF 推荐流实时调整结果
              </p>
              <div className="flex flex-wrap gap-2 max-w-lg justify-center">
                {QUICK_HINTS.map((hint) => (
                  <QuickHint key={hint} text={hint} />
                ))}
              </div>
            </div>
          )}

          {showSkeleton && <FeedSkeleton />}
        </div>

        {items.length > 0 && (
          <div className={`flex-1 min-h-[300px] flex flex-col ${embedded ? "px-2" : "px-4"} pb-2`}>
            <div className={`${embedded ? "px-0 pb-2" : "px-0 pb-3"}`}>
              <FeedMapOverview
                items={items}
                activePoiId={items[activeCardIndex]?.poi_id ?? null}
                onPoiSelect={(poiId) => {
                  const idx = items.findIndex((item) => item.poi_id === poiId);
                  if (idx >= 0) setActiveCardIndex(idx);
                }}
              />
            </div>
            <CardCarousel
              items={items}
              resetToken={`${sessionId}-${round}`}
              dimmed={dimCards}
              externalActiveIndex={activeCardIndex}
              onActiveIndexChange={setActiveCardIndex}
              getItemKey={(item) => `${item.poi_id}-${item.rank}`}
              className="h-full"
              renderItem={(item) => {
                const isSelected = selectedPoiIds.includes(item.poi_id);
                return (
                  <RecommendCard
                    item={item}
                    anchor={anchor}
                    dimmed={dimCards}
                    carousel
                    selectable
                    selected={isSelected}
                    selectionDisabled={selectionAtMax && !isSelected}
                    onOpenDetail={() => setDetailItem(item)}
                    onToggleSelect={() => toggleSelectPoi(item.poi_id)}
                  />
                );
              }}
            />
            <RefinementChips
              activeItem={items[activeCardIndex] ?? null}
              disabled={isRecommending}
            />
          </div>
        )}

        <div className={`${embedded ? "px-4 pb-4" : "max-w-5xl mx-auto px-6 pb-5"} space-y-4 shrink-0`}>
          {recommendToolCalls.length > 0 && (
            <ThoughtChain toolCalls={recommendToolCalls} />
          )}

          {recommendRationale && (
            <div
              className="rounded-xl overflow-hidden"
              style={{ border: "1px solid var(--border)", background: "var(--bg-surface)" }}
            >
              <button
                onClick={() => setRationaleOpen((v) => !v)}
                className="w-full flex items-center gap-2 px-3 py-2 text-[12px] hover:opacity-80 transition-colors"
              >
                {rationaleOpen ? (
                  <ChevronDown className="w-3.5 h-3.5" style={{ color: "var(--accent)" }} />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5" style={{ color: "var(--accent)" }} />
                )}
                <span className="font-medium" style={{ color: "var(--text-secondary)" }}>
                  推荐理由
                </span>
              </button>
              {rationaleOpen && (
                <pre
                  className="px-3 pb-3 text-[12px] whitespace-pre-wrap leading-relaxed font-sans"
                  style={{
                    color: "var(--text-secondary)",
                    borderTop: "1px solid var(--border)",
                  }}
                >
                  {recommendRationale}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>

      {detailItem && (
        <PoiDetailSheet
          item={detailItem}
          sessionId={sessionId}
          selected={selectedPoiIds.includes(detailItem.poi_id)}
          selectionDisabled={
            selectionAtMax && !selectedPoiIds.includes(detailItem.poi_id)
          }
          onClose={() => setDetailItem(null)}
          onToggleSelect={() => toggleSelectPoi(detailItem.poi_id)}
        />
      )}

      <ItineraryToolbar />
      <RecommendInput />
    </div>
  );
}
