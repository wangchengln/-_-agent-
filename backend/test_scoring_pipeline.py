#!/usr/bin/env python3
"""Integration tests for ScoringPipeline (Block H) — fakes, no network."""

from __future__ import annotations

from typing import Any, Callable

from domain.poi import POIItem
from domain.preference import PreferenceProfile
from domain.types import GeoLocation
from recsys.config import ScoringConfig
from recsys.scoring import ScoringPipeline


class FakeAmapClient:
    def __init__(self, *, around_results: list[POIItem] | None = None) -> None:
        self.around_results = around_results if around_results is not None else []

    def search_around(
        self,
        lng: float,
        lat: float,
        *,
        keywords: str | None = None,
        radius: int = 3000,
        types: str | None = None,
        sortrule: str = "weight",
        page: int = 1,
        offset: int = 20,
        anchor_city: str | None = None,
        keep_raw: bool = False,
    ) -> list[POIItem]:
        if page != 1:
            return []
        return list(self.around_results)


def _poi(
    poi_id: str,
    *,
    type: str = "风景名胜",
    rating: float | None = None,
    distance_m: float | None = None,
    tags: list[str] | None = None,
    description: str = "",
) -> POIItem:
    return POIItem(
        id=poi_id,
        name=poi_id,
        type=type,
        location=GeoLocation(lng=121.0, lat=31.0, city="上海"),
        rating=rating,
        distance_m=distance_m,
        tags=tags or [],
        description=description or poi_id,
    )


def _embed_from(mapping: dict[str, list[float]], dim: int = 3) -> Callable:
    def fn(texts: list[str]) -> list[list[float]]:
        return [mapping.get(text, [0.0] * dim) for text in texts]

    return fn


def _anchor_pref() -> PreferenceProfile:
    return PreferenceProfile.empty(
        anchor=GeoLocation(lng=121.47, lat=31.23, city="上海")
    )


def test_pipeline_end_to_end_filter_match_attenuate() -> None:
    pref = _anchor_pref()
    pref.positive_hard.categories = ["风景名胜"]
    pref.positive_hard.min_rating = 4.0
    pref.positive_soft.tags = ["文艺"]
    pref.negative_soft.dislike_tags = ["人多"]

    candidates = [
        _poi("p1", rating=4.5, distance_m=500.0, tags=["文艺"], description="文艺街区"),
        _poi("p2", rating=3.0, distance_m=200.0, description="低分景点"),  # filtered
        _poi("p3", rating=4.2, distance_m=300.0, tags=["人多"], description="嘈杂景点"),
        _poi("p4", rating=4.8, distance_m=1000.0, description="普通公园"),
    ]
    embed_fn = _embed_from(
        {
            "文艺": [1.0, 0.0, 0.0],
            "人多": [0.0, 1.0, 0.0],
            "文艺街区": [1.0, 0.0, 0.0],
            "嘈杂景点": [0.0, 1.0, 0.0],
            "普通公园": [0.0, 0.0, 1.0],
        }
    )
    pipeline = ScoringPipeline(
        ScoringConfig(),
        amap_client=FakeAmapClient(around_results=candidates),
        embed_fn=embed_fn,
    )

    feed = pipeline.run(pref, round=1, command="文艺一点，别去人多的", k=5)

    ids = feed.poi_ids
    assert "p2" not in ids  # filtered by min_rating
    assert ids == ["p1", "p4", "p3"]  # p3 dragged down by attenuator
    assert feed.total_candidates == 4
    # additive breakdown
    top = feed.items[0].breakdown
    assert abs(
        (top.matcher_semantic + top.matcher_collaborative + top.attenuator)
        - top.total
    ) < 1e-9
    print("pipeline end-to-end OK")


def test_pipeline_respects_k() -> None:
    pref = _anchor_pref()
    candidates = [_poi(f"p{i}", rating=4.0 + i * 0.1) for i in range(5)]
    pipeline = ScoringPipeline(
        ScoringConfig().model_copy(update={"k": 2}),
        amap_client=FakeAmapClient(around_results=candidates),
    )
    feed = pipeline.run(pref)
    assert len(feed.items) == 2
    print("pipeline respects k OK")


def test_pipeline_all_filtered_returns_empty_items() -> None:
    pref = _anchor_pref()
    pref.positive_hard.min_rating = 4.9  # nothing qualifies
    candidates = [_poi("p1", rating=4.0), _poi("p2", rating=3.5)]
    pipeline = ScoringPipeline(
        ScoringConfig(),
        amap_client=FakeAmapClient(around_results=candidates),
    )
    feed = pipeline.run(pref)
    assert feed.items == []
    assert feed.total_candidates == 2  # retrieved but all filtered
    print("pipeline all-filtered OK")


def test_pipeline_empty_pool() -> None:
    pref = _anchor_pref()
    pipeline = ScoringPipeline(
        ScoringConfig(),
        amap_client=FakeAmapClient(around_results=[]),
    )
    feed = pipeline.run(pref)
    assert feed.items == []
    assert feed.total_candidates == 0
    print("pipeline empty pool OK")


def test_orchestration_predicates() -> None:
    pipeline = ScoringPipeline()

    plain = PreferenceProfile.empty()
    assert pipeline._needs_filter(plain) is False
    assert pipeline._needs_matcher(plain) is False
    assert pipeline._needs_attenuator(plain) is False

    pref = PreferenceProfile.empty()
    pref.positive_hard.categories = ["风景名胜"]
    pref.positive_soft.tags = ["文艺"]
    pref.negative_soft.dislike_tags = ["人多"]
    assert pipeline._needs_filter(pref) is True
    assert pipeline._needs_matcher(pref) is True
    assert pipeline._needs_attenuator(pref) is True
    print("orchestration predicates OK")


def test_collaborative_only_when_no_soft_prefs() -> None:
    # No positive soft prefs => semantic skipped; embed_fn must not be called.
    pref = _anchor_pref()

    def boom(texts: list[str]) -> list[list[float]]:
        raise AssertionError("embedding must not run without soft prefs/negatives")

    candidates = [
        _poi("near", rating=4.0, distance_m=100.0),
        _poi("far", rating=4.0, distance_m=900.0),
    ]
    pipeline = ScoringPipeline(
        ScoringConfig(),
        amap_client=FakeAmapClient(around_results=candidates),
        embed_fn=boom,
    )
    feed = pipeline.run(pref)
    assert feed.poi_ids == ["near", "far"]  # collaborative ranks nearer first
    print("collaborative-only path OK")


if __name__ == "__main__":
    test_pipeline_end_to_end_filter_match_attenuate()
    test_pipeline_respects_k()
    test_pipeline_all_filtered_returns_empty_items()
    test_pipeline_empty_pool()
    test_orchestration_predicates()
    test_collaborative_only_when_no_soft_prefs()
    print("ALL TESTS PASSED")
