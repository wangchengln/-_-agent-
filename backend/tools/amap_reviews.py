"""Fetch real user reviews for an Amap POI.

The official Web Service ``place/detail`` API does not expose review text.
This module calls Amap's public comment list endpoint (same data source as the
Gaode mobile app) and normalizes the response into :class:`PoiReview`.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from domain.poi_detail import PoiReview

logger = logging.getLogger(__name__)

REVIEW_LIST_URL = "https://m5.amap.com/ws/shield/search_poi/review/list"
DEFAULT_TIMEOUT = 8.0
DEFAULT_PAGE_SIZE = 10


def _parse_rating(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return None
    if rating <= 0:
        return None
    if rating > 5 and rating <= 10:
        rating = rating / 2
    return min(max(rating, 0.0), 5.0)


def _extract_review_photos(raw: dict[str, Any]) -> list[str]:
    photos: list[str] = []
    for key in ("pics", "pic_info", "images", "photos"):
        field = raw.get(key)
        if isinstance(field, list):
            for item in field:
                if isinstance(item, str) and item.strip():
                    photos.append(item.strip())
                elif isinstance(item, dict):
                    url = item.get("url") or item.get("pic_url")
                    if url:
                        photos.append(str(url))
        elif isinstance(field, str) and field.strip():
            photos.extend(part.strip() for part in field.split(",") if part.strip())
    return photos


def _normalize_review(raw: dict[str, Any], index: int) -> PoiReview | None:
    content = (
        raw.get("review")
        or raw.get("content")
        or raw.get("review_content")
        or raw.get("desc")
        or raw.get("text")
        or ""
    )
    content = str(content).strip()
    if not content:
        return None

    author = (
        raw.get("user_name")
        or raw.get("username")
        or raw.get("nickname")
        or raw.get("author")
        or "匿名用户"
    )
    created_at = (
        raw.get("time")
        or raw.get("ctime")
        or raw.get("created_at")
        or raw.get("date")
    )
    review_id = raw.get("review_id") or raw.get("id") or raw.get("cid")

    return PoiReview(
        id=str(review_id) if review_id not in (None, "") else f"review-{index}",
        author=str(author).strip() or "匿名用户",
        rating=_parse_rating(raw.get("star") or raw.get("rating") or raw.get("score")),
        content=content,
        created_at=str(created_at).strip() if created_at not in (None, "") else None,
        photos=_extract_review_photos(raw),
        source="amap",
    )


def _extract_review_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("review_list", "reviews", "list", "items", "comment_list"):
            items = data.get(key)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
    for key in ("review_list", "reviews", "list"):
        items = payload.get(key)
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return []


def _extract_total(payload: dict[str, Any], fetched: int) -> int | None:
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("total", "total_count", "count", "review_count"):
            value = data.get(key)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    pass
    match = re.search(r'"total"\s*:\s*(\d+)', str(payload))
    if match:
        return int(match.group(1))
    return fetched if fetched > 0 else None


def fetch_poi_reviews(
    poi_id: str,
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[list[PoiReview], int | None, bool]:
    """Return (reviews, total_count, fetched_ok)."""
    poi_id = str(poi_id).strip()
    if not poi_id:
        return [], None, False

    params = {
        "poiid": poi_id,
        "page_num": 1,
        "page_size": max(1, min(page_size, 20)),
        "sort_type": 0,
        "version": "2.0",
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "application/json",
    }

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(REVIEW_LIST_URL, params=params, headers=headers)
            if response.status_code >= 400:
                logger.debug("amap reviews HTTP %s for %s", response.status_code, poi_id)
                return [], None, False
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.debug("amap reviews fetch failed for %s: %s", poi_id, exc)
        return [], None, False

    if str(payload.get("code", "1")) not in ("1", "0", "10000"):
        if payload.get("status") not in (1, "1", "ok", "OK"):
            logger.debug("amap reviews API error for %s: %s", poi_id, payload)
            return [], None, False

    reviews: list[PoiReview] = []
    for index, raw in enumerate(_extract_review_items(payload)):
        review = _normalize_review(raw, index)
        if review is not None:
            reviews.append(review)

    total = _extract_total(payload, len(reviews))
    return reviews, total, True
