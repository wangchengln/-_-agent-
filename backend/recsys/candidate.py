"""Candidate retrieval layer (recall) for the scoring pipeline.

Turns a :class:`PreferenceProfile` into a de-duplicated pool of nearby POIs by
calling Amap. This is the recall step that precedes the deterministic
Filter / Matcher / Attenuator / Aggregator stages.

Design choices:
- ``positive_hard.categories`` are routed to the Amap ``types`` parameter (the
  Amap top-level Chinese type names the Parser emits), while ``positive_soft``
  intent words go to ``keywords``. Keeping "what kind of place" (types) separate
  from "what vibe/feature" (keywords) avoids over-constraining a single query.
- With multiple categories we issue one query per category for diversity
  (Amap sorts by weight, so a single mixed query lets the dominant category
  crowd out the rest), then de-duplicate by POI id.
- Everything is synchronous to match the synchronous ``AmapClient`` (httpx).
  The Planner can wrap this in ``asyncio.to_thread`` when called from the API.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from domain.preference import PreferenceProfile
from domain.types import GeoLocation
from recsys.config import DEFAULT_SCORING_CONFIG, ScoringConfig
from recsys.types import CandidatePool
from tools.amap_client import AmapClientError, get_amap_client

logger = logging.getLogger(__name__)

# Amap place/around recommends offset (page size) <= 25.
_AMAP_PAGE_SIZE = 25
# Safety cap so pagination can never loop unbounded.
_MAX_PAGES = 4


class CandidateError(Exception):
    """Base error for the candidate retrieval layer."""


class AnchorResolutionError(CandidateError):
    """Raised when a search anchor cannot be resolved to coordinates."""


def resolve_anchor(
    preference: PreferenceProfile,
    *,
    client: Any | None = None,
) -> GeoLocation:
    """Resolve the preference anchor to coordinates usable by Amap.

    - If the anchor already has ``lng``/``lat`` it is returned unchanged.
    - Otherwise an ``address``/``city`` is geocoded via Amap.
    - If neither is available, :class:`AnchorResolutionError` is raised.
    """
    anchor = preference.anchor
    if anchor and anchor.lng is not None and anchor.lat is not None:
        return anchor

    if anchor and (anchor.address or anchor.city):
        client = client or get_amap_client()
        query = anchor.address or anchor.city
        assert query is not None  # narrowed by the condition above
        try:
            return client.geocode(query, city=anchor.city)
        except AmapClientError as exc:
            raise AnchorResolutionError(
                f"failed to geocode anchor {query!r}: {exc}"
            ) from exc

    raise AnchorResolutionError(
        "preference has no usable anchor (need coordinates, address, or city)"
    )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            merged.append(cleaned)
    return merged


def _build_search_keywords(preference: PreferenceProfile) -> str:
    """Build the Amap ``keywords`` OR-string from positive soft preferences.

    Categories are intentionally excluded here (they go to ``types``). Multiple
    keywords are joined with ``|``, which Amap treats as OR.
    """
    soft = preference.positive_soft
    parts = _dedupe([*soft.keywords, *soft.tags, *soft.cuisine_types])
    return "|".join(parts)


def _build_amap_types(preference: PreferenceProfile) -> str | None:
    """Build the Amap ``types`` parameter from positive hard categories."""
    categories = _dedupe(preference.positive_hard.categories)
    return "|".join(categories) if categories else None


def _merge_pool(
    pool: dict[str, Any],
    items: list[Any],
    limit: int,
) -> None:
    """Insert items into the id-keyed pool, de-duplicating, respecting limit."""
    for poi in items:
        if len(pool) >= limit:
            break
        pool.setdefault(poi.id, poi)


def _search_paged(
    client: Any,
    anchor: GeoLocation,
    *,
    keywords: str | None,
    types: str | None,
    radius: int,
    limit: int,
    anchor_city: str | None,
    sortrule: str = "weight",
) -> list[Any]:
    """Page through Amap nearby search until ``limit`` items or results run out."""
    collected: list[Any] = []
    for page in range(1, _MAX_PAGES + 1):
        if len(collected) >= limit:
            break
        items = client.search_around(
            anchor.lng,
            anchor.lat,
            keywords=keywords,
            radius=radius,
            types=types,
            sortrule=sortrule,
            page=page,
            offset=_AMAP_PAGE_SIZE,
            anchor_city=anchor_city,
        )
        if not items:
            break
        collected.extend(items)
        if len(items) < _AMAP_PAGE_SIZE:
            break
    return collected


def retrieve_candidates(
    preference: PreferenceProfile,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
    *,
    client: Any | None = None,
) -> CandidatePool:
    """Retrieve a de-duplicated POI candidate pool for the given preference.

    Strategy:
    1. Resolve anchor coordinates (geocoding if needed).
    2. If >1 category: one nearby search per category (diversity), else a single
       combined search.
    3. If the pool is still empty (cold start / over-constrained), fall back to a
       radius-only popularity search.
    4. De-duplicate by POI id and truncate to ``config.max_candidates``.
    """
    client = client or get_amap_client()
    anchor = resolve_anchor(preference, client=client)
    radius = preference.positive_hard.radius_m or config.default_radius_m
    keywords = _build_search_keywords(preference) or None
    categories = _dedupe(preference.positive_hard.categories)

    pool: dict[str, Any] = {}

    if len(categories) > 1:
        per_category_limit = max(
            _AMAP_PAGE_SIZE,
            math.ceil(config.max_candidates / len(categories)),
        )
        for category in categories:
            if len(pool) >= config.max_candidates:
                break
            try:
                items = _search_paged(
                    client,
                    anchor,
                    keywords=keywords,
                    types=category,
                    radius=radius,
                    limit=per_category_limit,
                    anchor_city=anchor.city,
                )
            except AmapClientError as exc:
                logger.warning("category query failed for %r: %s", category, exc)
                continue
            _merge_pool(pool, items, config.max_candidates)
    else:
        try:
            items = _search_paged(
                client,
                anchor,
                keywords=keywords,
                types=_build_amap_types(preference),
                radius=radius,
                limit=config.max_candidates,
                anchor_city=anchor.city,
            )
            _merge_pool(pool, items, config.max_candidates)
        except AmapClientError as exc:
            logger.warning("primary candidate query failed: %s", exc)

    if not pool:
        logger.info("candidate pool empty; running radius-only fallback search")
        items = _search_paged(
            client,
            anchor,
            keywords=None,
            types=None,
            radius=radius,
            limit=config.max_candidates,
            anchor_city=anchor.city,
        )
        _merge_pool(pool, items, config.max_candidates)

    return list(pool.values())[: config.max_candidates]
