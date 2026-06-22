#!/usr/bin/env python3
"""Tests for recsys candidate retrieval (Block C) — mocked AmapClient."""

from __future__ import annotations

from typing import Any, Callable

from domain.poi import POIItem
from domain.preference import PreferenceProfile
from domain.types import GeoLocation
from recsys.candidate import (
    AnchorResolutionError,
    _build_amap_types,
    _build_search_keywords,
    resolve_anchor,
    retrieve_candidates,
)
from recsys.config import ScoringConfig


class FakeAmapClient:
    """Records calls and returns configurable POI lists (no network)."""

    def __init__(
        self,
        *,
        geocode_result: GeoLocation | None = None,
        results_by_types: dict[str | None, list[POIItem]] | None = None,
        default_results: list[POIItem] | None = None,
        around_fn: Callable[[dict[str, Any]], list[POIItem]] | None = None,
    ) -> None:
        self.geocode_calls: list[tuple[str, str | None]] = []
        self.around_calls: list[dict[str, Any]] = []
        self.geocode_result = geocode_result
        self.results_by_types = results_by_types or {}
        self.default_results = default_results if default_results is not None else []
        self.around_fn = around_fn

    def geocode(self, address: str, *, city: str | None = None) -> GeoLocation:
        self.geocode_calls.append((address, city))
        if self.geocode_result is None:
            raise AssertionError("geocode called but not configured")
        return self.geocode_result

    def search_around(
        self,
        lng: float,
        lat: float,
        *,
        keywords: str | None = None,
        radius: int = 3000,
        types: str | None = None,
        sortrule: str = "distance",
        page: int = 1,
        offset: int = 20,
        anchor_city: str | None = None,
        keep_raw: bool = False,
    ) -> list[POIItem]:
        params = {
            "keywords": keywords,
            "types": types,
            "page": page,
            "radius": radius,
            "sortrule": sortrule,
        }
        self.around_calls.append(params)
        if self.around_fn is not None:
            return list(self.around_fn(params))
        if page != 1:
            return []
        if types in self.results_by_types:
            return list(self.results_by_types[types])
        return list(self.default_results)


def _poi(poi_id: str, name: str = "x", type: str = "风景名胜") -> POIItem:
    return POIItem(
        id=poi_id,
        name=name,
        type=type,
        location=GeoLocation(lng=121.0, lat=31.0, city="上海"),
    )


def _anchor() -> GeoLocation:
    return GeoLocation(lng=121.47, lat=31.23, city="上海")


def test_resolve_anchor_uses_existing_coords() -> None:
    pref = PreferenceProfile.empty(anchor=_anchor())
    client = FakeAmapClient()
    anchor = resolve_anchor(pref, client=client)
    assert anchor.lng == 121.47 and anchor.lat == 31.23
    assert client.geocode_calls == []
    print("resolve_anchor existing coords OK")


def test_resolve_anchor_geocodes_city() -> None:
    geo = GeoLocation(lng=121.0, lat=31.0, city="上海", address="上海市")
    client = FakeAmapClient(geocode_result=geo)
    pref = PreferenceProfile.empty(anchor=GeoLocation(city="上海"))
    anchor = resolve_anchor(pref, client=client)
    assert anchor.lng == 121.0
    assert client.geocode_calls == [("上海", "上海")]
    print("resolve_anchor geocode city OK")


def test_resolve_anchor_missing_raises() -> None:
    client = FakeAmapClient()
    pref = PreferenceProfile.empty()
    try:
        resolve_anchor(pref, client=client)
    except AnchorResolutionError:
        print("resolve_anchor missing guard OK")
        return
    raise AssertionError("expected AnchorResolutionError")


def test_build_search_keywords_merges_and_dedupes() -> None:
    pref = PreferenceProfile.empty()
    pref.positive_soft.keywords = ["拍照", "拍照"]
    pref.positive_soft.tags = ["文艺"]
    pref.positive_soft.cuisine_types = ["川菜"]
    assert _build_search_keywords(pref) == "拍照|文艺|川菜"
    assert _build_search_keywords(PreferenceProfile.empty()) == ""
    print("build_search_keywords OK")


def test_build_amap_types() -> None:
    pref = PreferenceProfile.empty()
    pref.positive_hard.categories = ["风景名胜", "科教文化服务", "风景名胜"]
    assert _build_amap_types(pref) == "风景名胜|科教文化服务"
    assert _build_amap_types(PreferenceProfile.empty()) is None
    print("build_amap_types OK")


def test_retrieve_dedupes_across_categories() -> None:
    pref = PreferenceProfile.empty(anchor=_anchor())
    pref.positive_hard.categories = ["风景名胜", "餐饮服务"]
    client = FakeAmapClient(
        results_by_types={
            "风景名胜": [_poi("1"), _poi("2"), _poi("3")],
            "餐饮服务": [_poi("3"), _poi("4")],
        }
    )
    pool = retrieve_candidates(pref, ScoringConfig(), client=client)
    ids = sorted(p.id for p in pool)
    assert ids == ["1", "2", "3", "4"]
    # one query per category (each finishes in a single page)
    assert len(client.around_calls) == 2
    print("retrieve dedupe across categories OK")


def test_retrieve_truncates_to_max_candidates() -> None:
    pref = PreferenceProfile.empty(anchor=_anchor())
    config = ScoringConfig().model_copy(update={"max_candidates": 3})
    client = FakeAmapClient(default_results=[_poi(str(i)) for i in range(10)])
    pool = retrieve_candidates(pref, config, client=client)
    assert len(pool) == 3
    print("retrieve truncation OK")


def test_retrieve_cold_start_fallback() -> None:
    pref = PreferenceProfile.empty(anchor=_anchor())
    pref.positive_soft.keywords = ["拍照"]

    def around_fn(params: dict[str, Any]) -> list[POIItem]:
        if params["keywords"] is None and params["types"] is None:
            return [_poi("99")]
        return []

    client = FakeAmapClient(around_fn=around_fn)
    pool = retrieve_candidates(pref, ScoringConfig(), client=client)
    assert [p.id for p in pool] == ["99"]
    # primary keyword query happened, then fallback query
    assert any(c["keywords"] == "拍照" for c in client.around_calls)
    assert any(
        c["keywords"] is None and c["types"] is None for c in client.around_calls
    )
    print("retrieve cold-start fallback OK")


def test_retrieve_geocodes_when_anchor_has_no_coords() -> None:
    geo = GeoLocation(lng=121.0, lat=31.0, city="上海")
    client = FakeAmapClient(
        geocode_result=geo,
        default_results=[_poi("a"), _poi("b")],
    )
    pref = PreferenceProfile.empty(anchor=GeoLocation(city="上海"))
    pool = retrieve_candidates(pref, ScoringConfig(), client=client)
    assert len(client.geocode_calls) == 1
    assert {p.id for p in pool} == {"a", "b"}
    print("retrieve geocode branch OK")


if __name__ == "__main__":
    test_resolve_anchor_uses_existing_coords()
    test_resolve_anchor_geocodes_city()
    test_resolve_anchor_missing_raises()
    test_build_search_keywords_merges_and_dedupes()
    test_build_amap_types()
    test_retrieve_dedupes_across_categories()
    test_retrieve_truncates_to_max_candidates()
    test_retrieve_cold_start_fallback()
    test_retrieve_geocodes_when_anchor_has_no_coords()
    print("ALL TESTS PASSED")
