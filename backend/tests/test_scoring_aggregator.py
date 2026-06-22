#!/usr/bin/env python3
"""Tests for recsys Aggregator tool (Block G) — pure, no network."""

from __future__ import annotations

from domain.feed import RecommendationFeed
from domain.poi import POIItem
from domain.preference import PreferenceProfile
from domain.types import GeoLocation
from recsys.aggregator import aggregate_and_rank, build_recommendation_feed
from recsys.attenuator import AttenuatorScore
from recsys.matcher import MatcherScores


def _poi(poi_id: str, *, distance_m: float | None = None) -> POIItem:
    return POIItem(
        id=poi_id,
        name=poi_id,
        type="风景名胜",
        location=GeoLocation(lng=121.0, lat=31.0, city="上海"),
        distance_m=distance_m,
    )


def _matcher(
    semantic_contribution: float = 0.0,
    collaborative_contribution: float = 0.0,
) -> MatcherScores:
    combined = semantic_contribution + collaborative_contribution
    return MatcherScores(
        semantic_contribution=semantic_contribution,
        collaborative_contribution=collaborative_contribution,
        combined=combined,
    )


def test_total_is_combined_plus_penalty() -> None:
    poi = _poi("p")
    matcher = {poi.id: _matcher(0.65, 0.175)}  # combined 0.825
    atten = {poi.id: AttenuatorScore(penalty=-0.05)}
    items = aggregate_and_rank([poi], matcher, atten, k=5)
    assert abs(items[0].score - (0.825 - 0.05)) < 1e-9
    print("total = combined + penalty OK")


def test_breakdown_is_additive() -> None:
    poi = _poi("p")
    matcher = {poi.id: _matcher(0.6, 0.2)}
    atten = {poi.id: AttenuatorScore(penalty=-0.1)}
    items = aggregate_and_rank([poi], matcher, atten, k=5)
    bd = items[0].breakdown
    assert bd is not None
    total_from_parts = (
        bd.matcher_semantic + bd.matcher_collaborative + bd.attenuator
    )
    assert abs(total_from_parts - bd.total) < 1e-9
    assert abs(bd.total - 0.7) < 1e-9
    assert bd.filter_passed is True
    print("breakdown additive OK")


def test_ranking_order_by_total_desc() -> None:
    a, b, c = _poi("a"), _poi("b"), _poi("c")
    matcher = {
        "a": _matcher(0.2, 0.0),
        "b": _matcher(0.9, 0.0),
        "c": _matcher(0.5, 0.0),
    }
    atten: dict[str, AttenuatorScore] = {}
    items = aggregate_and_rank([a, b, c], matcher, atten, k=3)
    assert [it.item.id for it in items] == ["b", "c", "a"]
    assert [it.rank for it in items] == [1, 2, 3]
    print("ranking by total OK")


def test_tie_break_by_distance() -> None:
    near = _poi("near", distance_m=100.0)
    far = _poi("far", distance_m=900.0)
    none_dist = _poi("none", distance_m=None)
    matcher = {
        "near": _matcher(0.5, 0.0),
        "far": _matcher(0.5, 0.0),
        "none": _matcher(0.5, 0.0),
    }
    items = aggregate_and_rank([far, none_dist, near], matcher, {}, k=3)
    # equal totals -> nearer first, missing distance last
    assert [it.item.id for it in items] == ["near", "far", "none"]
    print("tie-break by distance OK")


def test_truncates_to_k() -> None:
    pois = [_poi(str(i)) for i in range(10)]
    matcher = {p.id: _matcher(float(p.id) / 10.0, 0.0) for p in pois}
    items = aggregate_and_rank(pois, matcher, {}, k=3)
    assert len(items) == 3
    # highest contributions are 9, 8, 7
    assert [it.item.id for it in items] == ["9", "8", "7"]
    print("truncate to k OK")


def test_missing_scores_default_to_zero() -> None:
    poi = _poi("p")
    items = aggregate_and_rank([poi], {}, {}, k=5)
    assert items[0].score == 0.0
    assert items[0].breakdown.total == 0.0
    print("missing scores default OK")


def test_build_recommendation_feed() -> None:
    pref = PreferenceProfile.empty()
    a, b = _poi("a"), _poi("b")
    matcher = {"a": _matcher(0.8, 0.0), "b": _matcher(0.3, 0.0)}
    feed = build_recommendation_feed(
        [a, b],
        matcher,
        {},
        preference=pref,
        round=2,
        user_command="文艺一点",
        total_candidates=42,
        k=5,
    )
    assert isinstance(feed, RecommendationFeed)
    assert feed.round == 2
    assert feed.k == 5
    assert feed.user_command == "文艺一点"
    assert feed.total_candidates == 42
    assert feed.poi_ids == ["a", "b"]
    assert feed.items[0].rank == 1 and feed.items[1].rank == 2
    print("build_recommendation_feed OK")


def test_empty_pool_builds_empty_feed() -> None:
    pref = PreferenceProfile.empty()
    feed = build_recommendation_feed([], {}, {}, preference=pref, k=5)
    assert feed.items == []
    assert feed.total_candidates == 0
    print("empty pool feed OK")


def test_feed_round_trip_serialization() -> None:
    pref = PreferenceProfile.empty()
    poi = _poi("p", distance_m=500.0)
    matcher = {"p": _matcher(0.6, 0.2)}
    atten = {"p": AttenuatorScore(penalty=-0.05)}
    feed = build_recommendation_feed([poi], matcher, atten, preference=pref, k=5)
    dumped = feed.model_dump_json()
    restored = RecommendationFeed.model_validate_json(dumped)
    assert restored.items[0].breakdown.total == feed.items[0].breakdown.total
    print("feed serialization OK")


if __name__ == "__main__":
    test_total_is_combined_plus_penalty()
    test_breakdown_is_additive()
    test_ranking_order_by_total_desc()
    test_tie_break_by_distance()
    test_truncates_to_k()
    test_missing_scores_default_to_zero()
    test_build_recommendation_feed()
    test_empty_pool_builds_empty_feed()
    test_feed_round_trip_serialization()
    print("ALL TESTS PASSED")
