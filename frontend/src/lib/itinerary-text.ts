import type { WeekendItinerary } from "@/lib/recommend-types";
import {
  formatDurationMinutes,
  formatMeters,
  formatTransportMode,
} from "@/lib/recommend-types";

/** Plain-text itinerary for clipboard / share. */
export function buildItineraryShareText(itinerary: WeekendItinerary): string {
  const lines = [
    "周末行程",
    `${formatTransportMode(itinerary.transport_mode)} · ${itinerary.day_start}–${itinerary.day_end}`,
    `停留 ${formatDurationMinutes(itinerary.total_dwell_min)} · 通勤 ${formatDurationMinutes(itinerary.total_travel_min)} · ${formatMeters(itinerary.total_distance_m)}`,
    "",
  ];

  itinerary.stops.forEach((stop, index) => {
    lines.push(
      `${index + 1}. ${stop.name}`,
      `   ${stop.arrive_at}–${stop.leave_at} · 停留 ${stop.dwell_min} 分钟`,
      stop.address ? `   ${stop.address}` : ""
    );
    lines.push("");
  });

  if (itinerary.warnings.length > 0) {
    lines.push("提示：", ...itinerary.warnings.map((w) => `- ${w}`));
  }

  return lines.filter((line) => line !== undefined).join("\n").trim();
}

export async function copyItineraryToClipboard(
  itinerary: WeekendItinerary
): Promise<boolean> {
  const text = buildItineraryShareText(itinerary);
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
