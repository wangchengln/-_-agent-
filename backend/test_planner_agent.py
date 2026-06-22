#!/usr/bin/env python3
"""Tests for Planner Agent façade (Block H) — fakes, no network."""

from __future__ import annotations

import asyncio

from domain.irf_state import IRFSessionState
from domain.poi import POIItem
from domain.preference import PreferenceProfile
from domain.types import GeoLocation
from graph.planner_agent import (
    AnchorNotResolvedError,
    EmptyCandidatePoolError,
    PlannerAgent,
    PlannerInput,
)
from recsys.config import ScoringConfig
from recsys.scoring import ScoringPipeline


class FakeAmapClient:
    def __init__(self, *, around_results: list[POIItem] | None = None) -> None:
        self.around_results = around_results if around_results is not None else []

    def search_around(self, lng, lat, *, page=1, **kwargs) -> list[POIItem]:
        if page != 1:
            return []
        return list(self.around_results)


def _poi(poi_id: str, *, rating: float = 4.0, distance_m: float = 500.0) -> POIItem:
    return POIItem(
        id=poi_id,
        name=poi_id,
        type="风景名胜",
        location=GeoLocation(lng=121.0, lat=31.0, city="上海"),
        rating=rating,
        distance_m=distance_m,
        description=poi_id,
    )


def _anchor_pref() -> PreferenceProfile:
    return PreferenceProfile.empty(
        anchor=GeoLocation(lng=121.47, lat=31.23, city="上海")
    )


def _planner_with(candidates: list[POIItem]) -> PlannerAgent:
    pipeline = ScoringPipeline(
        ScoringConfig(),
        amap_client=FakeAmapClient(around_results=candidates),
        embed_fn=lambda texts: [[0.0, 0.0, 0.0] for _ in texts],
    )
    return PlannerAgent(pipeline)


def test_plan_returns_feed() -> None:
    planner = _planner_with([_poi("a", distance_m=100.0), _poi("b", distance_m=900.0)])
    pref = _anchor_pref()
    feed = asyncio.run(
        planner.plan(PlannerInput(preference=pref, round=3, user_command="走起", k=5))
    )
    assert feed.round == 3
    assert feed.user_command == "走起"
    assert feed.poi_ids == ["a", "b"]
    assert feed.items[0].breakdown is not None
    print("plan returns feed OK")


def test_plan_respects_k_override() -> None:
    planner = _planner_with([_poi(f"p{i}") for i in range(5)])
    feed = asyncio.run(
        planner.plan(PlannerInput(preference=_anchor_pref(), k=2))
    )
    assert len(feed.items) == 2
    print("plan k override OK")


def test_plan_anchor_not_resolved() -> None:
    planner = _planner_with([_poi("a")])
    pref = PreferenceProfile.empty()  # no anchor at all
    try:
        asyncio.run(planner.plan(PlannerInput(preference=pref)))
    except AnchorNotResolvedError:
        print("plan anchor-not-resolved OK")
        return
    raise AssertionError("expected AnchorNotResolvedError")


def test_plan_empty_candidate_pool() -> None:
    planner = _planner_with([])  # client returns nothing
    pref = _anchor_pref()
    try:
        asyncio.run(planner.plan(PlannerInput(preference=pref)))
    except EmptyCandidatePoolError:
        print("plan empty-pool OK")
        return
    raise AssertionError("expected EmptyCandidatePoolError")


def test_plan_for_session() -> None:
    planner = _planner_with([_poi("a"), _poi("b")])
    pref = _anchor_pref()
    pref.source_command = "上海周末"
    state = IRFSessionState(round=2, preference=pref)
    feed = asyncio.run(planner.plan_for_session(state))
    assert feed.round == 2
    assert feed.user_command == "上海周末"
    assert set(feed.poi_ids) == {"a", "b"}
    print("plan_for_session OK")


if __name__ == "__main__":
    test_plan_returns_feed()
    test_plan_respects_k_override()
    test_plan_anchor_not_resolved()
    test_plan_empty_candidate_pool()
    test_plan_for_session()
    print("ALL TESTS PASSED")
