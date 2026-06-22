"""Filter tool — hard-constraint enforcement (paper §3.3.1).

Removes candidates that violate any *hard* constraint, equivalent to assigning
them a score of -inf. Soft preferences are handled later by Matcher/Attenuator.

Rejection precedence (first failing rule wins, for explainable reasons):
  1. excluded_poi_id      negative_hard.exclude_poi_ids
  2. excluded_category    negative_hard.exclude_categories (substring of type)
  3. excluded_tag         negative_hard.exclude_tags
  4. category_mismatch    not in positive_hard.categories
  5. price_exceeded       cost_numeric > max_price
  6. rating_below_min     rating < min_rating
  7. distance_exceeded    distance_m > radius_m
  8. venue_type_mismatch  indoor/outdoor requirement

"Unknown" values (missing rating/price/distance, ambiguous venue) are kept on a
benefit-of-the-doubt basis so the pool isn't over-pruned; Matcher will rank them
down. ``open_now`` is intentionally skipped on Day 3 (Amap open-hour data is not
reliably parsed yet) and only logs a warning.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from domain.poi import POIItem
from domain.preference import (
    NegativeHardConstraints,
    PositiveHardConstraints,
    PreferenceProfile,
)
from domain.types import VenueType

logger = logging.getLogger(__name__)

_INDOOR_MARKERS = ("室内", "indoor")
_OUTDOOR_MARKERS = ("室外", "户外", "outdoor")

REASON_EXCLUDED_POI_ID = "excluded_poi_id"
REASON_EXCLUDED_CATEGORY = "excluded_category"
REASON_EXCLUDED_TAG = "excluded_tag"
REASON_CATEGORY_MISMATCH = "category_mismatch"
REASON_PRICE_EXCEEDED = "price_exceeded"
REASON_RATING_BELOW_MIN = "rating_below_min"
REASON_DISTANCE_EXCEEDED = "distance_exceeded"
REASON_VENUE_TYPE_MISMATCH = "venue_type_mismatch"


class RejectedCandidate(BaseModel):
    """A POI removed by the Filter, with a machine-readable reason."""

    item: POIItem
    reason: str


class FilterResult(BaseModel):
    """Outcome of applying hard constraints to a candidate pool."""

    passed: list[POIItem] = Field(default_factory=list)
    rejected: list[RejectedCandidate] = Field(default_factory=list)

    @property
    def passed_count(self) -> int:
        return len(self.passed)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)

    @property
    def rejected_pairs(self) -> list[tuple[POIItem, str]]:
        """Compatibility view as ``(item, reason)`` tuples."""
        return [(rc.item, rc.reason) for rc in self.rejected]

    def reason_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for rc in self.rejected:
            counts[rc.reason] = counts.get(rc.reason, 0) + 1
        return counts


def _clean(terms: list[str]) -> list[str]:
    return [term.strip() for term in terms if term.strip()]


def _type_contains_any(poi: POIItem, terms: list[str]) -> bool:
    return any(term in poi.type for term in _clean(terms))


def _tags_intersect(poi: POIItem, terms: list[str]) -> bool:
    tagset = {tag.strip() for tag in poi.tags if tag.strip()}
    return any(term in tagset for term in _clean(terms))


def _matches_category(poi: POIItem, categories: list[str]) -> bool:
    """True if the POI type contains a wanted category (empty list = no limit)."""
    wanted = _clean(categories)
    if not wanted:
        return True
    return any(category in poi.type for category in wanted)


def _is_excluded(poi: POIItem, negative_hard: NegativeHardConstraints) -> bool:
    """True if any hard exclusion (poi id / category / tag) matches."""
    excluded_ids = {pid.strip() for pid in negative_hard.exclude_poi_ids if pid.strip()}
    if poi.id in excluded_ids:
        return True
    if _type_contains_any(poi, negative_hard.exclude_categories):
        return True
    if _tags_intersect(poi, negative_hard.exclude_tags):
        return True
    return False


def _price_ok(poi: POIItem, hard: PositiveHardConstraints) -> bool:
    if hard.max_price is None or poi.cost_numeric is None:
        return True
    return poi.cost_numeric <= hard.max_price


def _rating_ok(poi: POIItem, hard: PositiveHardConstraints) -> bool:
    if hard.min_rating is None or poi.rating is None:
        return True
    return poi.rating >= hard.min_rating


def _distance_ok(poi: POIItem, hard: PositiveHardConstraints) -> bool:
    if hard.radius_m is None or poi.distance_m is None:
        return True
    return poi.distance_m <= hard.radius_m


def _passes_price_rating_distance(poi: POIItem, hard: PositiveHardConstraints) -> bool:
    return _price_ok(poi, hard) and _rating_ok(poi, hard) and _distance_ok(poi, hard)


def _venue_of(poi: POIItem) -> str | None:
    """Infer indoor/outdoor from tags + description; ``None`` if ambiguous."""
    blob = (" ".join(poi.tags) + " " + poi.description).lower()
    indoor = any(marker in blob for marker in _INDOOR_MARKERS)
    outdoor = any(marker in blob for marker in _OUTDOOR_MARKERS)
    if indoor and not outdoor:
        return VenueType.INDOOR.value
    if outdoor and not indoor:
        return VenueType.OUTDOOR.value
    return None


def _passes_venue_type(poi: POIItem, venue_type: VenueType) -> bool:
    if venue_type == VenueType.ANY:
        return True
    venue = _venue_of(poi)
    if venue is None:
        return True  # unknown -> keep, let Matcher decide
    return venue == venue_type.value


def _passes_open_now(poi: POIItem, require_open: bool) -> bool:
    """Day 3 degraded: open-hour data is unavailable, so never reject here."""
    return True


def _rejection_reason(poi: POIItem, preference: PreferenceProfile) -> str | None:
    """Return the first failing hard-constraint reason, or ``None`` if it passes."""
    hard = preference.positive_hard
    negative = preference.negative_hard

    excluded_ids = {pid.strip() for pid in negative.exclude_poi_ids if pid.strip()}
    if poi.id in excluded_ids:
        return REASON_EXCLUDED_POI_ID
    if _type_contains_any(poi, negative.exclude_categories):
        return REASON_EXCLUDED_CATEGORY
    if _tags_intersect(poi, negative.exclude_tags):
        return REASON_EXCLUDED_TAG
    if not _matches_category(poi, hard.categories):
        return REASON_CATEGORY_MISMATCH
    if not _price_ok(poi, hard):
        return REASON_PRICE_EXCEEDED
    if not _rating_ok(poi, hard):
        return REASON_RATING_BELOW_MIN
    if not _distance_ok(poi, hard):
        return REASON_DISTANCE_EXCEEDED
    if not _passes_venue_type(poi, hard.venue_type):
        return REASON_VENUE_TYPE_MISMATCH
    return None


def apply_filter(
    candidates: list[POIItem],
    preference: PreferenceProfile,
) -> FilterResult:
    """Partition candidates into passed / rejected by hard constraints."""
    if preference.positive_hard.open_now is True:
        logger.warning(
            "open_now requested but Amap open-hour data is unavailable; "
            "skipping open_now filter (Day 3 degraded)"
        )

    passed: list[POIItem] = []
    rejected: list[RejectedCandidate] = []
    for poi in candidates:
        reason = _rejection_reason(poi, preference)
        if reason is None:
            passed.append(poi)
        else:
            rejected.append(RejectedCandidate(item=poi, reason=reason))

    return FilterResult(passed=passed, rejected=rejected)
