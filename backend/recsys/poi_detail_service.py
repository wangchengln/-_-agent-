"""Build enriched POI detail for the frontend detail page."""

from __future__ import annotations

import asyncio
import logging

from domain.feed import ScoredPOIItem
from domain.poi import POIItem
from domain.poi_detail import PoiDetail, PoiReview
from graph.session_manager import SessionManager, session_manager
from recsys.loop import feed_item_payload
from tools.amap_client import AmapApiError, AmapClient, AmapClientError, get_amap_client
from tools.amap_reviews import fetch_poi_reviews

logger = logging.getLogger(__name__)


def _open_time_from_raw(raw: dict | None) -> str | None:
    if not raw:
        return None
    biz_ext = raw.get("biz_ext") or {}
    if not isinstance(biz_ext, dict):
        biz_ext = {}
    for key in ("open_time2", "open_time", "opentime"):
        value = biz_ext.get(key) or raw.get(key)
        if value not in (None, ""):
            text = str(value).strip()
            if text:
                return text
    business = raw.get("business") or {}
    if isinstance(business, dict):
        for key in ("opentime_week", "opentime_today"):
            value = business.get(key)
            if value not in (None, ""):
                text = str(value).strip()
                if text:
                    return text
    return None


def _website_from_raw(raw: dict | None) -> str | None:
    if not raw:
        return None
    for key in ("website", "site"):
        value = raw.get(key)
        if value not in (None, ""):
            text = str(value).strip()
            if text:
                return text
    return None


def _merge_photos(*sources: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for photos in sources:
        for url in photos:
            if url and url not in seen:
                seen.add(url)
                merged.append(url)
    return merged


def _find_feed_item(
    session_manager: SessionManager,
    session_id: str,
    poi_id: str,
) -> tuple[ScoredPOIItem | None, dict | None]:
    state = session_manager.get_irf_state(session_id)
    feed = state.current_feed
    if feed is None:
        return None, None
    for scored in feed.items:
        if scored.poi_id == poi_id:
            payload = feed_item_payload(scored, state.preference)
            return scored, payload
    return None, None


def _build_from_poi(
    poi: POIItem,
    *,
    feed_payload: dict | None = None,
    reviews: list[PoiReview] | None = None,
    reviews_total: int | None = None,
    reviews_fetched: bool = False,
) -> PoiDetail:
    raw = poi.raw or {}
    photos = _merge_photos(
        poi.photos,
        [str(p.get("url")) for p in raw.get("photos", []) if isinstance(p, dict) and p.get("url")],
    )
    if feed_payload:
        photos = _merge_photos(photos, feed_payload.get("photos") or [])

    rating = poi.rating
    cost = poi.cost
    distance_m = poi.distance_m
    score = None
    rank = None
    reason = None
    if feed_payload:
        rating = feed_payload.get("rating", rating)
        cost = feed_payload.get("cost", cost)
        distance_m = feed_payload.get("distance_m", distance_m)
        score = feed_payload.get("score")
        rank = feed_payload.get("rank")
        reason = feed_payload.get("reason")

    review_list = reviews or []
    reviews_source = "amap" if reviews_fetched and review_list else (
        "amap" if reviews_fetched else "unavailable"
    )

    return PoiDetail(
        poi_id=poi.id,
        name=poi.name,
        type=poi.type,
        address=poi.address,
        lng=poi.location.lng,
        lat=poi.location.lat,
        rating=rating,
        cost=cost,
        tel=poi.tel,
        open_time=_open_time_from_raw(raw),
        website=_website_from_raw(raw),
        tags=poi.tags,
        photos=photos,
        distance_m=distance_m,
        score=score,
        rank=rank,
        reason=reason,
        reviews=review_list,
        reviews_total=reviews_total if reviews_total is not None else len(review_list),
        reviews_fetched=reviews_fetched,
        reviews_source=reviews_source,
    )


class PoiDetailService:
    """Resolve POI detail by merging session feed cache and live Amap APIs."""

    def __init__(
        self,
        sessions: SessionManager | None = None,
        amap: AmapClient | None = None,
    ) -> None:
        self._sessions = sessions or session_manager
        self._amap = amap or get_amap_client()

    def get_detail(self, session_id: str, poi_id: str) -> PoiDetail:
        scored, feed_payload = _find_feed_item(self._sessions, session_id, poi_id)
        poi: POIItem | None = scored.item if scored is not None else None

        try:
            live_poi = self._amap.get_poi_detail(poi_id, keep_raw=True)
            if poi is None:
                poi = live_poi
            else:
                poi = self._merge_poi(poi, live_poi)
        except (AmapClientError, AmapApiError) as exc:
            logger.warning("poi detail fetch failed for %s: %s", poi_id, exc)
            if poi is None:
                raise

        reviews, reviews_total, reviews_fetched = fetch_poi_reviews(poi_id)
        return _build_from_poi(
            poi,
            feed_payload=feed_payload,
            reviews=reviews,
            reviews_total=reviews_total,
            reviews_fetched=reviews_fetched,
        )

    @staticmethod
    def _merge_poi(base: POIItem, live: POIItem) -> POIItem:
        """Prefer live detail fields while keeping feed distance/rank context."""
        merged_raw = live.raw or base.raw
        return POIItem(
            id=live.id,
            name=live.name or base.name,
            type=live.type or base.type,
            typecode=live.typecode or base.typecode,
            address=live.address or base.address,
            location=live.location if live.location.lng is not None else base.location,
            rating=live.rating if live.rating is not None else base.rating,
            cost=live.cost or base.cost,
            cost_numeric=live.cost_numeric if live.cost_numeric is not None else base.cost_numeric,
            distance_m=base.distance_m if base.distance_m is not None else live.distance_m,
            tel=live.tel or base.tel,
            tags=live.tags or base.tags,
            description=live.description or base.description,
            photos=_merge_photos(live.photos, base.photos),
            raw=merged_raw,
        )


poi_detail_service = PoiDetailService()


async def get_poi_detail_async(session_id: str, poi_id: str) -> PoiDetail:
    return await asyncio.to_thread(poi_detail_service.get_detail, session_id, poi_id)
