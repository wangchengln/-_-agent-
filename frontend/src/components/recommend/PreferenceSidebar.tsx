"use client";

import {
  Ban,
  CheckCircle2,
  Lightbulb,
  MapPin,
  NotebookPen,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { useApp } from "@/lib/store";
import type {
  PositiveHardConstraints,
  PreferenceProfile,
  VenueType,
} from "@/lib/recommend-types";
import { formatFeedDistance } from "@/lib/recommend-types";

interface Props {
  onClose: () => void;
}

const VENUE_LABELS: Record<VenueType, string> = {
  any: "不限",
  indoor: "室内",
  outdoor: "室外",
};

function Chip({ text, tone = "neutral" }: { text: string; tone?: "neutral" | "negative" }) {
  const negative = tone === "negative";
  return (
    <span
      className="px-2 py-0.5 rounded-full text-[11px]"
      style={{
        background: negative ? "rgba(239,68,68,0.1)" : "var(--accent-bg)",
        color: negative ? "#ef4444" : "var(--accent)",
        border: `1px solid ${negative ? "rgba(239,68,68,0.25)" : "var(--border-accent)"}`,
      }}
    >
      {text}
    </span>
  );
}

function ChipList({ items, tone }: { items: string[]; tone?: "neutral" | "negative" }) {
  if (items.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <Chip key={item} text={item} tone={tone} />
      ))}
    </div>
  );
}

function Section({
  icon: Icon,
  title,
  empty,
  children,
}: {
  icon: React.ElementType;
  title: string;
  empty?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-2">
      <div className="flex items-center gap-2">
        <Icon className="w-3.5 h-3.5" style={{ color: "var(--accent)" }} />
        <h3 className="text-[12px] font-semibold" style={{ color: "var(--text-primary)" }}>
          {title}
        </h3>
      </div>
      {empty ? (
        <p className="text-[11px] pl-5" style={{ color: "var(--text-muted)" }}>
          —
        </p>
      ) : (
        <div className="pl-5 space-y-1.5">{children}</div>
      )}
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline gap-2 text-[12px]">
      <span className="shrink-0" style={{ color: "var(--text-muted)" }}>
        {label}
      </span>
      <span style={{ color: "var(--text-secondary)" }}>{value}</span>
    </div>
  );
}

function buildAnchorText(pref: PreferenceProfile): string | null {
  const anchor = pref.anchor;
  if (!anchor) return null;
  const parts: string[] = [];
  if (anchor.city) parts.push(anchor.city);
  if (anchor.address) parts.push(anchor.address);
  else if (anchor.lat != null && anchor.lng != null) {
    parts.push(`${anchor.lat.toFixed(4)}, ${anchor.lng.toFixed(4)}`);
  }
  return parts.length > 0 ? parts.join(" · ") : null;
}

function hasHardConstraints(h: PositiveHardConstraints): boolean {
  return (
    h.radius_m != null ||
    h.categories.length > 0 ||
    h.max_price != null ||
    h.min_rating != null ||
    h.open_now === true ||
    h.venue_type !== "any"
  );
}

export default function PreferenceSidebar({ onClose }: Props) {
  const { preference, intentSummary, round, currentFeed } = useApp();

  const anchorText = preference ? buildAnchorText(preference) : null;
  const ph = preference?.positive_hard;
  const ps = preference?.positive_soft;
  const nh = preference?.negative_hard;
  const ns = preference?.negative_soft;

  const hardEmpty = !ph || !hasHardConstraints(ph);
  const softEmpty =
    !ps || (ps.tags.length === 0 && ps.keywords.length === 0 && ps.cuisine_types.length === 0);
  const negEmpty =
    (!nh ||
      (nh.exclude_categories.length === 0 &&
        nh.exclude_tags.length === 0 &&
        nh.exclude_poi_ids.length === 0)) &&
    (!ns || (ns.dislike_tags.length === 0 && ns.dislike_keywords.length === 0));

  return (
    <div className="flex flex-col h-full" style={{ background: "var(--bg-surface)" }}>
      {/* Header */}
      <div
        className="h-14 flex items-center justify-between px-4 shrink-0"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-4 h-4" style={{ color: "var(--accent)" }} />
          <span className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
            当前偏好
          </span>
          {round > 0 && (
            <span
              className="text-[10px] px-2 py-0.5 rounded-full"
              style={{ background: "var(--accent-bg)", color: "var(--accent)" }}
            >
              第 {round} 轮
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg transition-colors hover:opacity-80"
          style={{ color: "var(--text-muted)" }}
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Body */}
      {!preference ? (
        <div className="flex-1 flex items-center justify-center px-6">
          <div className="text-center">
            <SlidersHorizontal
              className="w-10 h-10 mx-auto mb-3"
              style={{ color: "var(--text-muted)", opacity: 0.4 }}
            />
            <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>
              暂无偏好
            </p>
            <p className="text-[11px] mt-1" style={{ color: "var(--text-muted)", opacity: 0.7 }}>
              发送一条推荐指令后，这里会显示解析出的结构化偏好
            </p>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
          {/* Anchor */}
          <Section icon={MapPin} title="锚点" empty={!anchorText}>
            <p className="text-[12px]" style={{ color: "var(--text-secondary)" }}>
              {anchorText}
            </p>
          </Section>

          {/* Positive hard */}
          <Section icon={CheckCircle2} title="硬约束" empty={hardEmpty}>
            {ph && ph.radius_m != null && (
              <Row label="半径" value={formatFeedDistance(ph.radius_m) ?? `${ph.radius_m}m`} />
            )}
            {ph && ph.max_price != null && <Row label="人均上限" value={`¥${ph.max_price}`} />}
            {ph && ph.min_rating != null && <Row label="最低评分" value={`${ph.min_rating}`} />}
            {ph && ph.open_now === true && <Row label="营业状态" value="营业中" />}
            {ph && ph.venue_type !== "any" && (
              <Row label="场地" value={VENUE_LABELS[ph.venue_type]} />
            )}
            {ph && ph.categories.length > 0 && (
              <div className="space-y-1">
                <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
                  类别
                </span>
                <ChipList items={ph.categories} />
              </div>
            )}
          </Section>

          {/* Positive soft */}
          <Section icon={Lightbulb} title="软偏好" empty={softEmpty}>
            {ps && ps.tags.length > 0 && <ChipList items={ps.tags} />}
            {ps && ps.keywords.length > 0 && <ChipList items={ps.keywords} />}
            {ps && ps.cuisine_types.length > 0 && <ChipList items={ps.cuisine_types} />}
          </Section>

          {/* Negative */}
          <Section icon={Ban} title="负向" empty={negEmpty}>
            {nh && nh.exclude_categories.length > 0 && (
              <ChipList items={nh.exclude_categories} tone="negative" />
            )}
            {nh && nh.exclude_tags.length > 0 && (
              <ChipList items={nh.exclude_tags} tone="negative" />
            )}
            {ns && ns.dislike_tags.length > 0 && (
              <ChipList items={ns.dislike_tags} tone="negative" />
            )}
            {ns && ns.dislike_keywords.length > 0 && (
              <ChipList items={ns.dislike_keywords} tone="negative" />
            )}
          </Section>

          {/* Intent / parser context */}
          <Section icon={NotebookPen} title="本轮理解" empty={!intentSummary}>
            <p className="text-[12px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>
              {intentSummary}
            </p>
          </Section>

          {currentFeed?.preference_summary && (
            <details
              className="rounded-lg overflow-hidden"
              style={{ border: "1px solid var(--border)" }}
            >
              <summary
                className="px-3 py-2 text-[11px] cursor-pointer select-none"
                style={{ color: "var(--text-muted)" }}
              >
                偏好原文 (P_t)
              </summary>
              <pre
                className="px-3 py-2 text-[11px] whitespace-pre-wrap leading-relaxed font-mono"
                style={{ color: "var(--text-secondary)", borderTop: "1px solid var(--border)" }}
              >
                {currentFeed.preference_summary}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
