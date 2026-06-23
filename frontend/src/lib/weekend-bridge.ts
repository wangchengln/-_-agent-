import type {
  FeedItem,
  PreferenceProfile,
  WeekendItinerary,
} from "@/lib/recommend-types";
import {
  formatDurationMinutes,
  formatMeters,
  formatTransportMode,
} from "@/lib/recommend-types";

export type WeekendRoute = "chat" | "recommend" | "both";

const CHAT_ONLY_PATTERNS: RegExp[] = [
  /解释/,
  /为什么推荐/,
  /什么意思/,
  /介绍一下自己/,
  /你是谁/,
  /写.*代码/,
  /python/i,
  /帮我写/,
  /天气怎么样/,
  /查询.*天气/,
];

const REFINE_PATTERNS: RegExp[] = [
  /不要/,
  /别去/,
  /排除/,
  /换一/,
  /再来/,
  /再近/,
  /再远/,
  /远一点/,
  /近一点/,
  /便宜/,
  /贵一点/,
  /室内/,
  /室外/,
  /人少/,
  /人太多/,
  /换一批/,
  /不喜欢/,
];

const PLAN_PATTERNS: RegExp[] = [
  /周末/,
  /出行/,
  /去哪/,
  /去哪儿/,
  /推荐/,
  /规划/,
  /行程/,
  /附近/,
  /咖啡/,
  /展览/,
  /散步/,
  /citywalk/i,
  /打卡/,
  /亲子/,
  /约会/,
  /吃饭/,
  /餐厅/,
  /玩/,
];

/** Classify chat input in weekend dual-column mode. */
export function classifyWeekendChatInput(
  text: string,
  hasFeed: boolean
): WeekendRoute {
  const trimmed = text.trim();
  if (!trimmed) return "chat";

  if (CHAT_ONLY_PATTERNS.some((pattern) => pattern.test(trimmed))) {
    return "chat";
  }

  if (hasFeed && REFINE_PATTERNS.some((pattern) => pattern.test(trimmed))) {
    return "recommend";
  }

  if (PLAN_PATTERNS.some((pattern) => pattern.test(trimmed))) {
    return hasFeed ? "both" : "both";
  }

  if (hasFeed && trimmed.length <= 24) {
    return "recommend";
  }

  return "chat";
}

export function buildPoiAskPrompt(
  item: FeedItem,
  context?: {
    intentSummary?: string;
    anchorCity?: string | null;
  }
): string {
  const lines = [
    `我想了解一下「${item.name}」是否适合这个周末去。`,
    item.reason ? `系统推荐理由：${item.reason}` : null,
    item.rating != null ? `评分：${item.rating}` : null,
    item.address ? `地址：${item.address}` : null,
    context?.intentSummary ? `当前偏好：${context.intentSummary}` : null,
    context?.anchorCity ? `城市：${context.anchorCity}` : null,
    "请结合我的偏好，说明优缺点、适合人群，以及是否值得加入行程。",
  ];
  return lines.filter(Boolean).join("\n");
}

export function buildDislikeCommand(name: string): string {
  return `不要去${name}，换类似的`;
}

export const REFINEMENT_CHIPS: { label: string; command: string }[] = [
  { label: "再近一点", command: "距离再近一点" },
  { label: "不要太远", command: "距离不要太远" },
  { label: "不要人多的", command: "不要人多的" },
  { label: "换室内", command: "换室内活动" },
  { label: "便宜一点", command: "人均便宜一点" },
  { label: "更文艺", command: "更文艺一点" },
];

export function formatPreferenceForMemory(
  preference: PreferenceProfile,
  lastCommand: string
): string {
  const anchor = preference.anchor?.city || preference.anchor?.address || "未指定";
  const hard = preference.positive_hard;
  const soft = preference.positive_soft;
  const neg = preference.negative_soft;

  const lines = [
    `- 更新时间：${new Date().toLocaleString("zh-CN")}`,
    `- 最近指令：${lastCommand}`,
    `- 锚点区域：${anchor}`,
  ];

  if (hard.categories.length > 0) {
    lines.push(`- 偏好类型：${hard.categories.join("、")}`);
  }
  if (hard.max_price != null) {
    lines.push(`- 人均上限：¥${hard.max_price}`);
  }
  if (hard.min_rating != null) {
    lines.push(`- 最低评分：${hard.min_rating}`);
  }
  if (hard.venue_type && hard.venue_type !== "any") {
    lines.push(`- 场域：${hard.venue_type === "indoor" ? "室内" : "室外"}`);
  }
  if (soft.tags.length > 0 || soft.keywords.length > 0) {
    lines.push(
      `- 氛围关键词：${[...soft.tags, ...soft.keywords].slice(0, 8).join("、")}`
    );
  }
  if (neg.dislike_tags.length > 0 || neg.dislike_keywords.length > 0) {
    lines.push(
      `- 不喜欢：${[...neg.dislike_tags, ...neg.dislike_keywords].slice(0, 6).join("、")}`
    );
  }

  return lines.join("\n");
}

export function buildItineraryCanvasHtml(itinerary: WeekendItinerary): string {
  const stopsHtml = itinerary.stops
    .map(
      (stop, index) => `
      <section style="margin-bottom:16px;padding:14px;border:1px solid #e8e0d4;border-radius:12px;background:#fff;">
        <div style="font-size:12px;color:#b8860b;font-weight:600;">第 ${index + 1} 站</div>
        <h3 style="margin:6px 0 4px;font-size:16px;">${stop.name}</h3>
        <p style="margin:0;font-size:12px;color:#666;">${stop.address || stop.type}</p>
        <p style="margin:8px 0 0;font-size:12px;color:#444;">${stop.arrive_at} – ${stop.leave_at} · 停留 ${stop.dwell_min} 分钟</p>
      </section>`
    )
    .join("");

  const legsHtml = itinerary.legs
    .map(
      (leg) => `
      <li style="margin-bottom:8px;font-size:12px;color:#555;">
        ${formatTransportMode(leg.mode)} · ${formatMeters(leg.distance_m)} · ${formatDurationMinutes(Math.max(1, Math.round(leg.duration_s / 60)))}
      </li>`
    )
    .join("");

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <style>
    body { font-family: "Segoe UI", sans-serif; margin: 0; padding: 20px; background: #fcfaf7; color: #1a1a1a; }
    h1 { font-size: 20px; margin: 0 0 8px; }
    .meta { font-size: 12px; color: #666; margin-bottom: 20px; }
  </style>
</head>
<body>
  <h1>周末行程时间轴</h1>
  <p class="meta">
    ${itinerary.day_start} – ${itinerary.stops[itinerary.stops.length - 1]?.leave_at ?? itinerary.day_end}
    · ${formatTransportMode(itinerary.transport_mode)}
    · 通勤 ${itinerary.total_travel_min} 分钟
  </p>
  ${stopsHtml}
  ${
    itinerary.legs.length > 0
      ? `<div style="margin-top:12px;padding:12px;border-radius:12px;background:#fff8eb;border:1px solid #f0e4c8;">
          <h4 style="margin:0 0 8px;font-size:13px;">路段概览</h4>
          <ul style="margin:0;padding-left:18px;">${legsHtml}</ul>
        </div>`
      : ""
  }
</body>
</html>`;
}
