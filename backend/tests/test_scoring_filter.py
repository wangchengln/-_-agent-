#!/usr/bin/env python3
"""Tests for recsys Filter tool (Block D) — pure, no network."""

from __future__ import annotations

from domain.poi import POIItem
from domain.preference import PreferenceProfile
from domain.types import GeoLocation, VenueType
from recsys.filter import (
    REASON_CATEGORY_MISMATCH,
    REASON_DISTANCE_EXCEEDED,
    REASON_EXCLUDED_CATEGORY,
    REASON_EXCLUDED_POI_ID,
    REASON_EXCLUDED_TAG,
    REASON_PRICE_EXCEEDED,
    REASON_RATING_BELOW_MIN,
    REASON_VENUE_TYPE_MISMATCH,
    apply_filter,
    _matches_category,
    _passes_venue_type,
)


def _poi(
    poi_id: str = "p",
    type: str = "风景名胜;历史建筑",
    tags: list[str] | None = None,
    rating: float | None = None,
    cost_numeric: float | None = None,
    distance_m: float | None = None,
    description: str = "",
) -> POIItem:
    return POIItem(
        id=poi_id,
        name=poi_id,
        type=type,
        location=GeoLocation(lng=121.0, lat=31.0, city="上海"),
        tags=tags or [],
        rating=rating,
        cost_numeric=cost_numeric,
        distance_m=distance_m,
        description=description,
    )


def _pref() -> PreferenceProfile:
    return PreferenceProfile.empty()


def _filter_one(poi: POIItem, pref: PreferenceProfile) -> str | None:
    result = apply_filter([poi], pref)
    if result.passed:
        return None
    return result.rejected[0].reason


# --- category match ---

def test_category_match_substring() -> None:
    assert _matches_category(_poi(type="风景名胜;公园"), ["风景名胜"]) is True
    assert _matches_category(_poi(type="餐饮服务;咖啡厅"), ["风景名胜"]) is False
    assert _matches_category(_poi(type="任意"), []) is True  # empty = no limit
    print("category match OK")


def test_category_mismatch_rejected() -> None:
    pref = _pref()
    pref.positive_hard.categories = ["科教文化服务"]
    assert _filter_one(_poi(type="餐饮服务;火锅"), pref) == REASON_CATEGORY_MISMATCH
    assert _filter_one(_poi(type="科教文化服务;博物馆"), pref) is None
    print("category mismatch reject OK")


# --- hard exclusions ---

def test_excluded_poi_id() -> None:
    pref = _pref()
    pref.negative_hard.exclude_poi_ids = ["bad1"]
    assert _filter_one(_poi(poi_id="bad1"), pref) == REASON_EXCLUDED_POI_ID
    assert _filter_one(_poi(poi_id="ok"), pref) is None
    print("excluded poi id OK")


def test_excluded_category() -> None:
    pref = _pref()
    pref.negative_hard.exclude_categories = ["购物服务"]
    assert _filter_one(_poi(type="购物服务;商场"), pref) == REASON_EXCLUDED_CATEGORY
    print("excluded category OK")


def test_excluded_tag() -> None:
    pref = _pref()
    pref.negative_hard.exclude_tags = ["大型综合体"]
    assert _filter_one(_poi(tags=["大型综合体", "室内"]), pref) == REASON_EXCLUDED_TAG
    assert _filter_one(_poi(tags=["文艺"]), pref) is None
    print("excluded tag OK")


# --- price / rating / distance ---

def test_price_filter() -> None:
    pref = _pref()
    pref.positive_hard.max_price = 100.0
    assert _filter_one(_poi(cost_numeric=150.0), pref) == REASON_PRICE_EXCEEDED
    assert _filter_one(_poi(cost_numeric=80.0), pref) is None
    assert _filter_one(_poi(cost_numeric=None), pref) is None  # unknown kept
    print("price filter OK")


def test_rating_filter() -> None:
    pref = _pref()
    pref.positive_hard.min_rating = 4.0
    assert _filter_one(_poi(rating=3.5), pref) == REASON_RATING_BELOW_MIN
    assert _filter_one(_poi(rating=4.6), pref) is None
    assert _filter_one(_poi(rating=None), pref) is None  # unknown kept
    print("rating filter OK")


def test_distance_filter() -> None:
    pref = _pref()
    pref.positive_hard.radius_m = 3000
    assert _filter_one(_poi(distance_m=5000.0), pref) == REASON_DISTANCE_EXCEEDED
    assert _filter_one(_poi(distance_m=1200.0), pref) is None
    assert _filter_one(_poi(distance_m=None), pref) is None  # unknown kept
    print("distance filter OK")


# --- venue type ---

def test_venue_type_predicate() -> None:
    outdoor_poi = _poi(tags=["室外", "自然"])
    indoor_poi = _poi(tags=["室内", "展览"])
    unknown_poi = _poi(tags=["文艺"])
    assert _passes_venue_type(outdoor_poi, VenueType.OUTDOOR) is True
    assert _passes_venue_type(indoor_poi, VenueType.OUTDOOR) is False
    assert _passes_venue_type(unknown_poi, VenueType.OUTDOOR) is True  # benefit of doubt
    assert _passes_venue_type(indoor_poi, VenueType.ANY) is True
    print("venue type predicate OK")


def test_venue_type_filter() -> None:
    pref = _pref()
    pref.positive_hard.venue_type = VenueType.OUTDOOR
    assert _filter_one(_poi(tags=["室内"]), pref) == REASON_VENUE_TYPE_MISMATCH
    assert _filter_one(_poi(tags=["室外"]), pref) is None
    print("venue type filter OK")


# --- open_now degraded ---

def test_open_now_skipped() -> None:
    pref = _pref()
    pref.positive_hard.open_now = True
    # No open-hour data => must NOT reject on Day 3.
    assert _filter_one(_poi(poi_id="x"), pref) is None
    print("open_now skipped OK")


# --- integration ---

def test_apply_filter_partition_and_counts() -> None:
    pref = _pref()
    pref.positive_hard.categories = ["风景名胜"]
    pref.positive_hard.min_rating = 4.0
    pref.negative_hard.exclude_tags = ["网红"]

    candidates = [
        _poi(poi_id="keep1", type="风景名胜;公园", rating=4.5),
        _poi(poi_id="keep2", type="风景名胜;历史建筑", rating=None),  # unknown rating kept
        _poi(poi_id="drop_cat", type="餐饮服务;火锅", rating=4.8),
        _poi(poi_id="drop_rate", type="风景名胜;公园", rating=3.0),
        _poi(poi_id="drop_tag", type="风景名胜;公园", rating=4.9, tags=["网红"]),
    ]
    result = apply_filter(candidates, pref)
    passed_ids = {p.id for p in result.passed}
    assert passed_ids == {"keep1", "keep2"}
    assert result.passed_count == 2
    assert result.rejected_count == 3
    counts = result.reason_counts()
    assert counts.get(REASON_CATEGORY_MISMATCH) == 1
    assert counts.get(REASON_RATING_BELOW_MIN) == 1
    assert counts.get(REASON_EXCLUDED_TAG) == 1
    assert len(result.rejected_pairs) == 3
    print("apply_filter partition OK")


def test_exclusion_precedes_category() -> None:
    # A POI matching both an exclusion and the wanted category reports exclusion.
    pref = _pref()
    pref.positive_hard.categories = ["购物服务"]
    pref.negative_hard.exclude_categories = ["购物服务"]
    assert _filter_one(_poi(type="购物服务;商场"), pref) == REASON_EXCLUDED_CATEGORY
    print("exclusion precedence OK")


if __name__ == "__main__":
    test_category_match_substring()
    test_category_mismatch_rejected()
    test_excluded_poi_id()
    test_excluded_category()
    test_excluded_tag()
    test_price_filter()
    test_rating_filter()
    test_distance_filter()
    test_venue_type_predicate()
    test_venue_type_filter()
    test_open_now_skipped()
    test_apply_filter_partition_and_counts()
    test_exclusion_precedes_category()
    print("ALL TESTS PASSED")
