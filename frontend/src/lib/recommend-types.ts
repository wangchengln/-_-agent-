/**
 * IRF recommendation types — aligned with backend SSE payloads from
 * `recsys/loop.py` (feed_event, intent_event, error_event, done_event).
 *
 * Feed cards use the slim `feed_item_payload` view (not full POIItem / ScoreBreakdown).
 */

// ── Shared domain ──────────────────────────────────────────

/** Matches `domain.types.VenueType`. */
export type VenueType = "any" | "indoor" | "outdoor";

/** Matches `domain.types.GeoLocation`. */
export interface GeoLocation {
  lng: number | null;
  lat: number | null;
  city: string | null;
  adcode: string | null;
  address: string | null;
}

// ── Preference profile P_t (four quadrants) ──────────────

/** Matches `domain.preference.PositiveHardConstraints`. */
export interface PositiveHardConstraints {
  radius_m: number | null;
  categories: string[];
  max_price: number | null;
  min_rating: number | null;
  open_now: boolean | null;
  venue_type: VenueType;
}

/** Matches `domain.preference.PositiveSoftPreferences`. */
export interface PositiveSoftPreferences {
  tags: string[];
  keywords: string[];
  cuisine_types: string[];
}

/** Matches `domain.preference.NegativeHardConstraints`. */
export interface NegativeHardConstraints {
  exclude_categories: string[];
  exclude_poi_ids: string[];
  exclude_tags: string[];
}

/** Matches `domain.preference.NegativeSoftPreferences`. */
export interface NegativeSoftPreferences {
  dislike_tags: string[];
  dislike_keywords: string[];
}

/** Matches `domain.preference.PreferenceProfile` (JSON from feed SSE). */
export interface PreferenceProfile {
  version: number;
  anchor: GeoLocation | null;
  positive_hard: PositiveHardConstraints;
  positive_soft: PositiveSoftPreferences;
  negative_hard: NegativeHardConstraints;
  negative_soft: NegativeSoftPreferences;
  updated_at: number;
  source_command: string | null;
}

// ── Feed card (slim payload) ─────────────────────────────

/**
 * One card in the recommendation feed R_t.
 * Matches `recsys.loop.feed_item_payload` (not full `ScoredPOIItem`).
 */
export interface FeedItem {
  rank: number;
  poi_id: string;
  name: string;
  type: string;
  /** GCJ-02 longitude from POIItem.location; null when Amap omits coords. */
  lng: number | null;
  /** GCJ-02 latitude from POIItem.location; null when Amap omits coords. */
  lat: number | null;
  rating: number | null;
  distance_m: number | null;
  cost: string | null;
  address: string;
  tags: string[];
  photos: string[];
  score: number | null;
  /** Human-readable explanation from score breakdown + preference. */
  reason: string;
}

/** SSE `feed` event payload.
 * Matches `recsys.loop.feed_event`.
 */
export interface WeatherSnapshot {
  city: string;
  adcode: string;
  summary: string;
  temperature: string | null;
  is_rainy: boolean;
  injected_rule: string | null;
  fetched: boolean;
}

export interface RecommendFeedPayload {
  round: number;
  k: number;
  total_candidates: number | null;
  items: FeedItem[];
  preference: PreferenceProfile;
  /** Compact four-quadrant text from `PreferenceProfile.to_parser_context()`. */
  preference_summary: string;
  /** Weather context for this round; null when anchor missing or fetch skipped. */
  weather: WeatherSnapshot | null;
}

// ── Other SSE event payloads ───────────────────────────────

/** SSE `intent` event — Parser output summary. */
export interface RecommendIntentPayload {
  intent_summary: string;
  /** Backend uses "high" | "medium" | "low". */
  confidence: string;
  needs_clarification: boolean;
}

/** Stable error codes from `recsys.errors.ERROR_CODES`. */
export type RecommendErrorCode =
  | "invalid_command"
  | "parse_failed"
  | "anchor_missing"
  | "empty_pool"
  | "internal_error";

export const RECOMMEND_ERROR_CODES: readonly RecommendErrorCode[] = [
  "invalid_command",
  "parse_failed",
  "anchor_missing",
  "empty_pool",
  "internal_error",
] as const;

/**
 * Actionable follow-up commands per error code.
 * Clicking a chip re-sends it as the next IRF command.
 */
export const RECOMMEND_ERROR_SUGGESTIONS: Record<RecommendErrorCode, string[]> = {
  invalid_command: ["上海周末想找个文艺的咖啡馆"],
  parse_failed: ["上海徐汇区，文艺一点的室外活动", "杭州西湖边适合散步的地方"],
  anchor_missing: ["上海", "徐汇区附近", "杭州西湖边"],
  empty_pool: ["距离远一点也行", "换一个区域", "放宽评分要求"],
  internal_error: [],
};

/** SSE `error` event payload. */
export interface RecommendErrorPayload {
  code: RecommendErrorCode;
  message: string;
  retry_hint?: string | null;
  session_id?: string;
  round?: number;
}

/** SSE `done` event payload. */
export interface RecommendDonePayload {
  session_id: string;
  round: number;
}

/** SSE `token` event — streamed recommendation rationale. */
export interface RecommendTokenPayload {
  content: string;
}

/** SSE `tool_start` / `tool_end` for IRF pipeline stages. */
export interface RecommendToolPayload {
  tool: string;
  input?: string | Record<string, unknown>;
  output?: string | Record<string, unknown>;
}

// ── Aggregated round state (frontend store) ────────────────

/** Client-side snapshot after a successful IRF round. */
export interface RecommendRoundState {
  feed: RecommendFeedPayload;
  intent?: RecommendIntentPayload;
  rationale: string;
  toolCalls: RecommendToolPayload[];
}

// ── Type guards ────────────────────────────────────────────

export function isRecommendErrorCode(value: unknown): value is RecommendErrorCode {
  return (
    typeof value === "string" &&
    (RECOMMEND_ERROR_CODES as readonly string[]).includes(value)
  );
}

export function isFeedItem(value: unknown): value is FeedItem {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  return (
    typeof item.rank === "number" &&
    typeof item.poi_id === "string" &&
    typeof item.name === "string" &&
    (item.lng === null || typeof item.lng === "number") &&
    (item.lat === null || typeof item.lat === "number") &&
    typeof item.reason === "string" &&
    Array.isArray(item.tags) &&
    Array.isArray(item.photos)
  );
}

export function isRecommendFeedPayload(value: unknown): value is RecommendFeedPayload {
  if (!value || typeof value !== "object") return false;
  const payload = value as Record<string, unknown>;
  return (
    typeof payload.round === "number" &&
    typeof payload.k === "number" &&
    Array.isArray(payload.items) &&
    payload.items.every(isFeedItem) &&
    typeof payload.preference === "object" &&
    payload.preference !== null &&
    typeof payload.preference_summary === "string" &&
    (payload.weather === null ||
      (typeof payload.weather === "object" && payload.weather !== null))
  );
}

export function isRecommendErrorPayload(value: unknown): value is RecommendErrorPayload {
  if (!value || typeof value !== "object") return false;
  const payload = value as Record<string, unknown>;
  return (
    isRecommendErrorCode(payload.code) && typeof payload.message === "string"
  );
}

// ── Display helpers (shared by feed cards) ─────────────────

/** Format distance for card UI; mirrors backend `_format_distance`. */
export function formatFeedDistance(distanceM: number | null | undefined): string | null {
  if (distanceM == null) return null;
  if (distanceM >= 1000) return `${(distanceM / 1000).toFixed(1)}km`;
  return `${Math.round(distanceM)}m`;
}

/** Build Amap marker URI when lng/lat are known (from preference anchor or future POI coords). */
export function buildAmapMarkerUrl(
  lng: number,
  lat: number,
  name: string
): string {
  const params = new URLSearchParams({
    position: `${lng},${lat}`,
    name,
  });
  return `https://uri.amap.com/marker?${params.toString()}`;
}

// ── Itinerary (Day 6.3 / 6.4 / 6.5) ───────────────────────

export type TransportMode = "walking" | "driving" | "transit";

export const MIN_ITINERARY_STOPS = 2;
export const MAX_ITINERARY_STOPS = 5;

export interface ItineraryStop {
  order: number;
  poi_id: string;
  name: string;
  type: string;
  lng: number | null;
  lat: number | null;
  address: string;
  arrive_at: string;
  leave_at: string;
  dwell_min: number;
}

export interface ItineraryLeg {
  from_poi_id: string;
  to_poi_id: string;
  mode: TransportMode;
  distance_m: number;
  duration_s: number;
  depart_at: string;
  arrive_at: string;
  path: number[][];
  estimated: boolean;
}

export interface WeekendItinerary {
  session_id: string;
  round: number | null;
  anchor: GeoLocation | null;
  transport_mode: TransportMode;
  day_start: string;
  day_end: string;
  stops: ItineraryStop[];
  legs: ItineraryLeg[];
  total_distance_m: number;
  total_travel_min: number;
  total_dwell_min: number;
  weather: WeatherSnapshot | null;
  warnings: string[];
  generated_at: number;
}

export interface BuildItineraryRequest {
  session_id: string;
  poi_ids: string[];
  transport_mode?: TransportMode;
  day_start?: string;
  day_end?: string;
  anchor_poi_id?: string | null;
}

export interface BuildItineraryResponse {
  itinerary: WeekendItinerary;
  warnings: string[];
}

export type ItineraryErrorCode =
  | "no_feed"
  | "poi_not_found"
  | "missing_coords"
  | "invalid_anchor_poi"
  | "internal_error";

export const ITINERARY_ERROR_CODES: readonly ItineraryErrorCode[] = [
  "no_feed",
  "poi_not_found",
  "missing_coords",
  "invalid_anchor_poi",
  "internal_error",
] as const;

export interface ItineraryErrorPayload {
  code: ItineraryErrorCode;
  message: string;
}

export function isItineraryErrorCode(value: unknown): value is ItineraryErrorCode {
  return (
    typeof value === "string" &&
    (ITINERARY_ERROR_CODES as readonly string[]).includes(value)
  );
}

export function isWeekendItinerary(value: unknown): value is WeekendItinerary {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return Array.isArray(v.stops) && typeof v.transport_mode === "string";
}

export function isBuildItineraryResponse(value: unknown): value is BuildItineraryResponse {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return isWeekendItinerary(v.itinerary);
}

/** Format itinerary summary line for toolbar / toast. */
export function formatItinerarySummary(itinerary: WeekendItinerary): string {
  const last = itinerary.stops[itinerary.stops.length - 1];
  const end = last?.leave_at ?? itinerary.day_end;
  return `${itinerary.stops.length} 站 · ${itinerary.day_start}–${end} · 通勤 ${itinerary.total_travel_min} 分钟`;
}

const TRANSPORT_LABELS: Record<TransportMode, string> = {
  walking: "步行",
  driving: "驾车",
  transit: "公交",
};

export function formatTransportMode(mode: TransportMode): string {
  return TRANSPORT_LABELS[mode];
}

/** Format meters for leg / total distance display. */
export function formatMeters(distanceM: number): string {
  if (distanceM >= 1000) return `${(distanceM / 1000).toFixed(1)} km`;
  return `${Math.round(distanceM)} m`;
}

export function formatDurationMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes} 分钟`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h} 小时 ${m} 分钟` : `${h} 小时`;
}
