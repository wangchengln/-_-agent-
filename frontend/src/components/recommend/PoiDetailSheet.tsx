"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Clock,
  ExternalLink,
  Loader2,
  MapPin,
  MessageCircle,
  Phone,
  Route,
  Star,
  ThumbsDown,
  X,
} from "lucide-react";
import { getPoiDetail } from "@/lib/api";
import type { FeedItem, PoiDetail } from "@/lib/recommend-types";
import {
  buildAmapMarkerUrl,
  formatFeedDistance,
  isPoiDetail,
} from "@/lib/recommend-types";
import { buildDislikeCommand } from "@/lib/weekend-bridge";
import { useApp } from "@/lib/store";
import PoiDetailMap from "./PoiDetailMap";

interface Props {
  item: FeedItem;
  sessionId: string;
  selected?: boolean;
  selectionDisabled?: boolean;
  onClose: () => void;
  onToggleSelect?: () => void;
}

function formatCost(cost: string | null | undefined): string | null {
  if (!cost) return "免费";
  const trimmed = cost.trim();
  if (!trimmed || trimmed === "0" || trimmed === "0.00") return "免费";
  if (/^\d/.test(trimmed)) return `¥${trimmed.replace(/\.?0+$/, "")}`;
  return trimmed;
}

function ReviewStars({ rating }: { rating: number | null }) {
  if (rating == null) return null;
  return (
    <span className="inline-flex items-center gap-0.5 text-[11px]" style={{ color: "var(--accent)" }}>
      <Star className="w-3 h-3 fill-current" />
      {rating.toFixed(1)}
    </span>
  );
}

export default function PoiDetailSheet({
  item,
  sessionId,
  selected = false,
  selectionDisabled = false,
  onClose,
  onToggleSelect,
}: Props) {
  const { askAboutPoi, sendRecommendCommand, isRecommending } = useApp();
  const [detail, setDetail] = useState<PoiDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [photoIndex, setPhotoIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setDetail(null);
    setPhotoIndex(0);

    getPoiDetail(sessionId, item.poi_id)
      .then((payload) => {
        if (cancelled) return;
        if (isPoiDetail(payload)) {
          setDetail(payload);
        } else {
          setError("详情数据格式无效");
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "加载详情失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId, item.poi_id]);

  const display = detail ?? {
    poi_id: item.poi_id,
    name: item.name,
    type: item.type,
    address: item.address,
    lng: item.lng,
    lat: item.lat,
    rating: item.rating,
    cost: item.cost,
    tel: null,
    open_time: null,
    website: null,
    tags: item.tags,
    photos: item.photos,
    distance_m: item.distance_m,
    score: item.score,
    rank: item.rank,
    reason: item.reason,
    reviews: [],
    reviews_total: null,
    reviews_fetched: false,
    reviews_source: "unavailable",
  };

  const photos = useMemo(
    () => (display.photos.length > 0 ? display.photos : item.photos),
    [display.photos, item.photos]
  );
  const metaParts: string[] = [];
  if (display.rating != null) metaParts.push(`${display.rating.toFixed(1)} 分`);
  const distance = formatFeedDistance(display.distance_m);
  if (distance) metaParts.push(distance);
  const cost = formatCost(display.cost);
  if (cost) metaParts.push(cost);
  if (display.rank != null) metaParts.push(`推荐 #${display.rank}`);

  const mapUrl =
    display.lng != null && display.lat != null
      ? buildAmapMarkerUrl(display.lng, display.lat, display.name)
      : null;

  return (
    <div
      className="fixed inset-0 z-[120] flex justify-end animate-fade-in"
      style={{ background: "rgba(0,0,0,0.45)" }}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`${display.name} 详情`}
    >
      <div
        className="w-full sm:max-w-lg h-full max-h-screen overflow-hidden flex flex-col shadow-2xl animate-slide-in-right"
        style={{ background: "var(--bg-surface)", borderLeft: "1px solid var(--border)" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Hero gallery */}
        <div className="relative shrink-0" style={{ background: "var(--accent-bg)" }}>
          <div className="aspect-[16/10] overflow-hidden">
            {photos.length > 0 ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={photos[photoIndex] ?? photos[0]}
                alt={display.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-[12px]" style={{ color: "var(--text-muted)" }}>
                暂无图片
              </div>
            )}
          </div>
          {photos.length > 1 && (
            <div className="absolute bottom-3 left-0 right-0 flex justify-center gap-1.5">
              {photos.slice(0, 6).map((_, index) => (
                <button
                  key={index}
                  type="button"
                  aria-label={`第 ${index + 1} 张图片`}
                  onClick={() => setPhotoIndex(index)}
                  className="rounded-full transition-all"
                  style={{
                    width: index === photoIndex ? 14 : 6,
                    height: 6,
                    background: index === photoIndex ? "#fff" : "rgba(255,255,255,0.55)",
                  }}
                />
              ))}
            </div>
          )}
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭"
            className="absolute top-3 right-3 w-8 h-8 rounded-full flex items-center justify-center shadow-md"
            style={{ background: "rgba(0,0,0,0.5)", color: "#fff" }}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-5 space-y-5">
            {loading && (
              <div className="flex items-center gap-2 text-[12px]" style={{ color: "var(--text-muted)" }}>
                <Loader2 className="w-4 h-4 animate-spin" style={{ color: "var(--accent)" }} />
                正在加载高德详情与评价…
              </div>
            )}

            {error && (
              <div
                className="flex items-start gap-2 px-3 py-2 rounded-lg text-[12px]"
                style={{
                  background: "rgba(234, 179, 8, 0.12)",
                  border: "1px solid rgba(234, 179, 8, 0.35)",
                  color: "var(--text-secondary)",
                }}
              >
                <AlertTriangle className="w-4 h-4 shrink-0 text-amber-500 mt-0.5" />
                <span>{error}（已展示卡片缓存信息）</span>
              </div>
            )}

            <div>
              <h2 className="text-xl font-semibold leading-snug" style={{ color: "var(--text-primary)" }}>
                {display.name}
              </h2>
              <p className="text-[12px] mt-1" style={{ color: "var(--text-muted)" }}>
                {display.type.replace(/;/g, " · ")}
              </p>
              {metaParts.length > 0 && (
                <p className="text-[13px] mt-2 flex items-center gap-1.5" style={{ color: "var(--text-secondary)" }}>
                  <Star className="w-3.5 h-3.5 shrink-0" style={{ color: "var(--accent)" }} />
                  {metaParts.join(" · ")}
                </p>
              )}
            </div>

            {display.reason && (
              <section
                className="rounded-xl px-3 py-2.5 text-[12px] leading-relaxed"
                style={{ background: "var(--accent-bg)", border: "1px solid var(--border-accent)" }}
              >
                <p className="font-medium mb-1" style={{ color: "var(--accent)" }}>
                  为什么推荐你
                </p>
                <p style={{ color: "var(--text-secondary)" }}>{display.reason}</p>
              </section>
            )}

            {display.lng != null && display.lat != null && (
              <section className="space-y-2">
                <h3 className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
                  位置
                </h3>
                <PoiDetailMap lng={display.lng} lat={display.lat} name={display.name} />
                {display.address && (
                  <div className="flex items-start gap-2 text-[12px]" style={{ color: "var(--text-secondary)" }}>
                    <MapPin className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "var(--accent)" }} />
                    <span>{display.address}</span>
                  </div>
                )}
                {mapUrl && (
                  <a
                    href={mapUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-[12px] font-medium"
                    style={{ color: "var(--accent)" }}
                  >
                    在高德地图中打开
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </section>
            )}

            <section className="space-y-2">
              <h3 className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
                基本信息
              </h3>
              <div className="grid gap-2 text-[12px]" style={{ color: "var(--text-secondary)" }}>
                {display.tel && (
                  <div className="flex items-center gap-2">
                    <Phone className="w-4 h-4 shrink-0" style={{ color: "var(--accent)" }} />
                    <a href={`tel:${display.tel.split(";")[0]}`} className="hover:opacity-80">
                      {display.tel.replace(/;/g, " / ")}
                    </a>
                  </div>
                )}
                {display.open_time && (
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 shrink-0" style={{ color: "var(--accent)" }} />
                    <span>{display.open_time}</span>
                  </div>
                )}
                {display.website && (
                  <div className="flex items-center gap-2">
                    <ExternalLink className="w-4 h-4 shrink-0" style={{ color: "var(--accent)" }} />
                    <a
                      href={display.website.startsWith("http") ? display.website : `https://${display.website}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="truncate hover:opacity-80"
                    >
                      {display.website}
                    </a>
                  </div>
                )}
              </div>
              {display.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {display.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 rounded-full text-[10px]"
                      style={{
                        background: "var(--bg-page)",
                        color: "var(--text-secondary)",
                        border: "1px solid var(--border)",
                      }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </section>

            <section className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
                  用户评价
                </h3>
                {display.reviews_total != null && display.reviews_total > 0 && (
                  <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
                    共 {display.reviews_total} 条
                  </span>
                )}
              </div>

              {display.reviews.length > 0 ? (
                <div className="space-y-3">
                  {display.reviews.map((review, index) => (
                    <article
                      key={review.id ?? `review-${index}`}
                      className="rounded-xl p-3 space-y-2"
                      style={{ border: "1px solid var(--border)", background: "var(--bg-page)" }}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>
                          {review.author}
                        </span>
                        <ReviewStars rating={review.rating} />
                      </div>
                      <p className="text-[12px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                        {review.content}
                      </p>
                      {review.created_at && (
                        <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                          {review.created_at}
                        </p>
                      )}
                      {review.photos.length > 0 && (
                        <div className="flex gap-2 overflow-x-auto">
                          {review.photos.slice(0, 3).map((url) => (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              key={url}
                              src={url}
                              alt="评价图片"
                              className="w-16 h-16 rounded-lg object-cover shrink-0"
                            />
                          ))}
                        </div>
                      )}
                    </article>
                  ))}
                  <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                    评价内容来自高德地图用户
                  </p>
                </div>
              ) : (
                <div
                  className="rounded-xl px-3 py-4 text-center text-[12px]"
                  style={{ border: "1px dashed var(--border)", color: "var(--text-muted)" }}
                >
                  {display.reviews_fetched
                    ? "该地点暂无公开用户评价"
                    : "暂时无法拉取用户评价，请稍后再试或在高德地图查看"}
                </div>
              )}
            </section>
          </div>
        </div>

        {/* Footer actions */}
        <div
          className="shrink-0 p-4 flex flex-col gap-2"
          style={{ borderTop: "1px solid var(--border)", background: "var(--bg-surface)" }}
        >
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                askAboutPoi(item);
                onClose();
              }}
              className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-opacity hover:opacity-90"
              style={{
                color: "var(--accent)",
                border: "1px solid var(--border-accent)",
                background: "var(--accent-bg)",
              }}
            >
              <MessageCircle className="w-4 h-4" />
              问 AI
            </button>
            <button
              type="button"
              disabled={isRecommending}
              onClick={() => {
                void sendRecommendCommand(buildDislikeCommand(item.name));
                onClose();
              }}
              className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-opacity hover:opacity-90 disabled:opacity-40"
              style={{
                color: "#dc2626",
                border: "1px solid rgba(239, 68, 68, 0.25)",
                background: "rgba(239, 68, 68, 0.08)",
              }}
            >
              <ThumbsDown className="w-4 h-4" />
              不喜欢
            </button>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                if (!selectionDisabled || selected) {
                  onToggleSelect?.();
                }
              }}
              disabled={selectionDisabled && !selected}
              className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-opacity hover:opacity-90 disabled:opacity-40"
              style={{
                background: selected ? "var(--accent)" : "var(--accent-bg)",
                color: selected ? "#fff" : "var(--accent)",
                border: selected ? "none" : "1px solid var(--border-accent)",
              }}
            >
              <Route className="w-4 h-4" />
              {selected ? "已加入行程" : "加入行程"}
            </button>
            {mapUrl && (
              <a
                href={mapUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-lg text-[13px] font-medium transition-opacity hover:opacity-80"
                style={{
                  color: "var(--text-secondary)",
                  border: "1px solid var(--border)",
                  background: "var(--bg-page)",
                }}
              >
                <MapPin className="w-4 h-4" />
                导航
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
