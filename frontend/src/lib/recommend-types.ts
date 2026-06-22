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

/**
 * SSE `feed` event payload.
 * Matches `recsys.loop.feed_event`.
 */
export interface RecommendFeedPayload {
  round: number;
  k: number;
  total_candidates: number | null;
  items: FeedItem[];
  preference: PreferenceProfile;
  /** Compact four-quadrant text from `PreferenceProfile.to_parser_context()`. */
  preference_summary: string;
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
    typeof payload.preference_summary === "string"
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
