"use client";

import { Check, ExternalLink, ImageOff, MapPin, Route, Star } from "lucide-react";
import type { FeedItem, GeoLocation } from "@/lib/recommend-types";
import { formatFeedDistance } from "@/lib/recommend-types";

interface Props {
  item: FeedItem;
  anchor?: GeoLocation | null;
  dimmed?: boolean;
  /** Carousel layout: card opens detail; separate itinerary button */
  carousel?: boolean;
  selectable?: boolean;
  selected?: boolean;
  selectionDisabled?: boolean;
  onOpenDetail?: () => void;
  onToggleSelect?: () => void;
}

function formatCost(cost: string | null): string | null {
  if (!cost) return "免费";
  const trimmed = cost.trim();
  if (!trimmed || trimmed === "0" || trimmed === "0.00") return "免费";
  if (/^\d/.test(trimmed)) return `¥${trimmed.replace(/\.?0+$/, "")}`;
  return trimmed;
}

function buildMapSearchUrl(item: FeedItem, anchor?: GeoLocation | null): string {
  const keyword = [item.name, item.address].filter(Boolean).join(" ");
  const params = new URLSearchParams({ keyword });
  if (anchor?.city) params.set("city", anchor.city);
  if (anchor?.lng != null && anchor?.lat != null) {
    params.set("center", `${anchor.lng},${anchor.lat}`);
  }
  return `https://uri.amap.com/search?${params.toString()}`;
}

function buildMetaLine(item: FeedItem): string {
  const parts: string[] = [];
  if (item.rating != null) parts.push(`${item.rating.toFixed(1)}`);
  const distance = formatFeedDistance(item.distance_m);
  if (distance) parts.push(distance);
  const cost = formatCost(item.cost);
  if (cost) parts.push(cost);
  return parts.join(" · ");
}

export default function RecommendCard({
  item,
  anchor,
  dimmed,
  carousel = false,
  selectable = false,
  selected = false,
  selectionDisabled = false,
  onOpenDetail,
  onToggleSelect,
}: Props) {
  const photo = item.photos[0];
  const meta = buildMetaLine(item);
  const mapUrl = buildMapSearchUrl(item, anchor);
  const showSelectOnCover = selectable && !carousel;

  const handleCardClick = () => {
    if (carousel && onOpenDetail) {
      onOpenDetail();
      return;
    }
    if (!selectable || selectionDisabled || !onToggleSelect) return;
    onToggleSelect();
  };

  return (
    <article
      onClick={handleCardClick}
      className={`rounded-xl overflow-hidden transition-all animate-fade-in-scale ${
        dimmed ? "opacity-60" : ""
      } ${carousel || selectable ? "cursor-pointer" : ""} ${
        selectionDisabled && !selected && !carousel ? "opacity-75" : ""
      }`}
      style={{
        background: "var(--bg-surface)",
        border: selected
          ? "2px solid var(--accent)"
          : "1px solid var(--border)",
        boxShadow: selected ? "0 0 0 1px var(--accent-bg)" : undefined,
      }}
    >
      {/* Cover */}
      <div className="relative aspect-[16/10] overflow-hidden" style={{ background: "var(--accent-bg)" }}>
        {photo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={photo}
            alt={item.name}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center gap-2">
            <ImageOff className="w-8 h-8" style={{ color: "var(--text-muted)", opacity: 0.5 }} />
            <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
              {item.type.split(";")[0] || "POI"}
            </span>
          </div>
        )}
        <span
          className="absolute top-2 left-2 px-2 py-0.5 rounded-md text-[11px] font-semibold"
          style={{ background: "rgba(0,0,0,0.55)", color: "#fff" }}
        >
          #{item.rank}
        </span>
        {showSelectOnCover && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              if (!selectionDisabled || selected) {
                onToggleSelect?.();
              }
            }}
            disabled={selectionDisabled && !selected}
            aria-pressed={selected}
            aria-label={selected ? "取消选择" : "选择此站点"}
            className="absolute top-2 right-2 w-7 h-7 rounded-full flex items-center justify-center transition-all disabled:opacity-40"
            style={{
              background: selected ? "var(--accent)" : "var(--bg-surface)",
              border: selected ? "none" : "1px solid var(--border)",
              color: selected ? "#fff" : "var(--text-muted)",
            }}
          >
            {selected ? <Check className="w-4 h-4" /> : null}
          </button>
        )}
        {carousel && selected && (
          <span
            className="absolute top-2 right-2 px-2 py-0.5 rounded-md text-[10px] font-medium"
            style={{ background: "var(--accent)", color: "#fff" }}
          >
            已选
          </span>
        )}
        {!selectable && item.score != null && (
          <span
            className="absolute top-2 right-2 px-2 py-0.5 rounded-md text-[10px] font-mono"
            style={{ background: "var(--bg-surface)", color: "var(--accent)" }}
          >
            {item.score.toFixed(2)}
          </span>
        )}
        {selectable && item.score != null && (
          <span
            className="absolute bottom-2 right-2 px-2 py-0.5 rounded-md text-[10px] font-mono"
            style={{ background: "rgba(0,0,0,0.55)", color: "#fff" }}
          >
            {item.score.toFixed(2)}
          </span>
        )}
      </div>

      {/* Body */}
      <div className={`${carousel ? "p-3.5" : "p-4"} space-y-2.5`}>
        <div>
          <h3
            className={`${carousel ? "text-[14px]" : "text-[15px]"} font-semibold leading-snug line-clamp-2`}
            style={{ color: "var(--text-primary)" }}
          >
            {item.name}
          </h3>
          <p className="text-[11px] mt-0.5 truncate" style={{ color: "var(--text-muted)" }}>
            {item.type.replace(/;/g, " · ")}
          </p>
        </div>

        {meta && (
          <div className="flex items-center gap-1.5 text-[12px]" style={{ color: "var(--text-secondary)" }}>
            {item.rating != null && <Star className="w-3.5 h-3.5 shrink-0" style={{ color: "var(--accent)" }} />}
            <span>{meta}</span>
          </div>
        )}

        {item.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {item.tags.slice(0, carousel ? 3 : 4).map((tag) => (
              <span
                key={tag}
                className="px-2 py-0.5 rounded-full text-[10px]"
                style={{
                  background: "var(--accent-bg)",
                  color: "var(--accent)",
                  border: "1px solid var(--border-accent)",
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        <p
          className={`${carousel ? "text-[11px] line-clamp-3" : "text-[12px]"} leading-relaxed`}
          style={{ color: "var(--text-secondary)" }}
        >
          {item.reason}
        </p>

        {carousel ? (
          <div className="flex gap-2 pt-0.5" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              onClick={() => {
                if (!selectionDisabled || selected) {
                  onToggleSelect?.();
                }
              }}
              disabled={selectionDisabled && !selected}
              className="flex-1 inline-flex items-center justify-center gap-1 px-2.5 py-2 rounded-lg text-[11px] font-medium transition-opacity hover:opacity-90 disabled:opacity-40"
              style={{
                background: selected ? "var(--accent)" : "var(--accent-bg)",
                color: selected ? "#fff" : "var(--accent)",
                border: selected ? "none" : "1px solid var(--border-accent)",
              }}
            >
              <Route className="w-3.5 h-3.5" />
              {selected ? "已加入" : "加入行程"}
            </button>
            <button
              type="button"
              onClick={onOpenDetail}
              className="px-2.5 py-2 rounded-lg text-[11px] font-medium transition-opacity hover:opacity-80"
              style={{
                color: "var(--text-secondary)",
                border: "1px solid var(--border)",
                background: "var(--bg-page)",
              }}
            >
              详情
            </button>
          </div>
        ) : (
          <a
            href={mapUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1.5 text-[11px] font-medium transition-opacity hover:opacity-80"
            style={{ color: "var(--accent)" }}
          >
            <MapPin className="w-3.5 h-3.5" />
            在高德地图查看
            <ExternalLink className="w-3 h-3 opacity-70" />
          </a>
        )}
      </div>
    </article>
  );
}
