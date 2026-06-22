#!/usr/bin/env python3
"""Tests for the IRF interaction loop (Day 4, 4.2) — fakes, no network."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from domain.irf_state import ParserOutput
from domain.poi import POIItem
from domain.preference import PreferenceProfile
from domain.types import GeoLocation
from graph.planner_agent import PlannerAgent
from graph.session_manager import SessionManager
from recsys.config import ScoringConfig
from recsys.errors import MAX_COMMAND_LENGTH
from recsys.loop import IRFLoop, LoopEvent
from recsys.scoring import ScoringPipeline


class FakeParser:
    """Returns a preset ParserOutput; records the input it received."""

    def __init__(self, output: ParserOutput) -> None:
        self._output = output
        self.calls: list = []

    async def parse(self, parser_input, **_kwargs) -> ParserOutput:
        self.calls.append(parser_input)
        return self._output


class FakeAmapClient:
    def __init__(self, around_results: list[POIItem]) -> None:
        self.around_results = around_results

    def search_around(self, lng, lat, *, page=1, **kwargs) -> list[POIItem]:
        return list(self.around_results) if page == 1 else []


def _poi(poi_id: str, *, rating: float = 4.5, distance_m: float = 300.0) -> POIItem:
    return POIItem(
        id=poi_id,
        name=poi_id,
        type="风景名胜",
        location=GeoLocation(lng=121.0, lat=31.0, city="上海"),
        rating=rating,
        distance_m=distance_m,
        description=poi_id,
    )


def _anchor_pref(*, tags: list[str] | None = None) -> PreferenceProfile:
    pref = PreferenceProfile.empty(anchor=GeoLocation(lng=121.47, lat=31.23, city="上海"))
    if tags:
        pref.positive_soft.tags = tags
    return pref


def _parser_output(
    pref: PreferenceProfile,
    summary: str = "想找文艺去处",
    *,
    confidence: str = "high",
) -> ParserOutput:
    return ParserOutput(preference=pref, intent_summary=summary, confidence=confidence)


def _planner_with(candidates: list[POIItem]) -> PlannerAgent:
    pipeline = ScoringPipeline(
        ScoringConfig(),
        amap_client=FakeAmapClient(candidates),
        embed_fn=lambda texts: [[0.1, 0.2, 0.3] for _ in texts],
    )
    return PlannerAgent(pipeline)


def _sessions() -> SessionManager:
    manager = SessionManager()
    manager.initialize(Path(tempfile.mkdtemp()))
    return manager


async def _collect(loop: IRFLoop, session_id: str, command: str) -> list[LoopEvent]:
    return [ev async for ev in loop.run_round(session_id, command)]


def test_single_round_event_sequence() -> None:
    sessions = _sessions()
    sessions.create_session("s1")
    loop = IRFLoop(
        parser=FakeParser(_parser_output(_anchor_pref(tags=["文艺"]))),
        planner=_planner_with([_poi("a", distance_m=100), _poi("b", distance_m=800)]),
        sessions=sessions,
    )
    events = asyncio.run(_collect(loop, "s1", "上海周末想找个文艺的地方"))
    types = [e.type for e in events]

    assert types[0] == "intent"
    assert "feed" in types
    assert types[-1] == "done"
    assert types.count("stage") == 2  # planner start + end

    feed_ev = next(e for e in events if e.type == "feed")
    assert feed_ev.payload["round"] == 1
    assert [item["poi_id"] for item in feed_ev.payload["items"]] == ["a", "b"]
    assert feed_ev.payload["items"][0]["reason"]  # non-empty rationale
    assert "preference" in feed_ev.payload
    print("single round event sequence OK")


def test_state_persisted_after_round() -> None:
    sessions = _sessions()
    sessions.create_session("s2")
    loop = IRFLoop(
        parser=FakeParser(_parser_output(_anchor_pref(tags=["自然"]))),
        planner=_planner_with([_poi("x")]),
        sessions=sessions,
    )
    asyncio.run(_collect(loop, "s2", "想去自然的地方"))

    state = sessions.get_irf_state("s2")
    assert state.round == 2  # advanced from 1 -> 2 for next turn
    assert state.preference.positive_soft.tags == ["自然"]
    assert state.command_history == ["想去自然的地方"]
    assert state.current_feed is not None
    assert state.current_feed.round == 1  # feed labeled with pre-increment round
    print("state persisted after round OK")


def test_two_rounds_round_increments() -> None:
    sessions = _sessions()
    sessions.create_session("s3")
    parser = FakeParser(_parser_output(_anchor_pref(tags=["文艺"])))
    loop = IRFLoop(
        parser=parser,
        planner=_planner_with([_poi("a"), _poi("b")]),
        sessions=sessions,
    )
    asyncio.run(_collect(loop, "s3", "第一条命令"))
    events2 = asyncio.run(_collect(loop, "s3", "不要太远"))

    feed_ev = next(e for e in events2 if e.type == "feed")
    assert feed_ev.payload["round"] == 2  # second feed is round 2

    # second round's parser saw R_t and the prior command in history
    second_input = parser.calls[1]
    assert second_input.feed is not None
    assert "第一条命令" in second_input.command_history
    print("two rounds round increments OK")


def test_anchor_missing_not_persisted() -> None:
    sessions = _sessions()
    sessions.create_session("s4")
    # parser output has NO anchor -> planner raises AnchorNotResolvedError
    loop = IRFLoop(
        parser=FakeParser(_parser_output(PreferenceProfile.empty())),
        planner=_planner_with([_poi("a")]),
        sessions=sessions,
    )
    events = asyncio.run(_collect(loop, "s4", "随便逛逛"))
    err = next(e for e in events if e.type == "error")
    assert err.payload["code"] == "anchor_missing"
    assert err.payload.get("retry_hint")
    assert err.payload.get("session_id") == "s4"
    assert err.payload.get("round") == 1
    stages = [e for e in events if e.type == "stage"]
    assert len(stages) == 2
    assert stages[-1].payload["status"] == "end"

    state = sessions.get_irf_state("s4")
    assert state.round == 1  # round NOT burned on failure
    assert state.current_feed is None
    print("anchor missing not persisted OK")


def test_empty_pool_not_persisted() -> None:
    sessions = _sessions()
    sessions.create_session("s5")
    loop = IRFLoop(
        parser=FakeParser(_parser_output(_anchor_pref())),
        planner=_planner_with([]),  # no candidates -> EmptyCandidatePoolError
        sessions=sessions,
    )
    events = asyncio.run(_collect(loop, "s5", "上海周末"))
    err = next(e for e in events if e.type == "error")
    assert err.payload["code"] == "empty_pool"

    state = sessions.get_irf_state("s5")
    assert state.round == 1
    assert state.current_feed is None
    print("empty pool not persisted OK")


def test_invalid_empty_command() -> None:
    sessions = _sessions()
    sessions.create_session("s6")
    loop = IRFLoop(
        parser=FakeParser(_parser_output(_anchor_pref())),
        planner=_planner_with([_poi("a")]),
        sessions=sessions,
    )
    events = asyncio.run(_collect(loop, "s6", "   "))
    err = next(e for e in events if e.type == "error")
    assert err.payload["code"] == "invalid_command"
    assert sessions.get_irf_state("s6").round == 1
    print("invalid empty command OK")


def test_invalid_long_command() -> None:
    sessions = _sessions()
    sessions.create_session("s7")
    loop = IRFLoop(
        parser=FakeParser(_parser_output(_anchor_pref())),
        planner=_planner_with([_poi("a")]),
        sessions=sessions,
    )
    events = asyncio.run(_collect(loop, "s7", "x" * (MAX_COMMAND_LENGTH + 1)))
    err = next(e for e in events if e.type == "error")
    assert err.payload["code"] == "invalid_command"
    print("invalid long command OK")


def test_low_confidence_still_plans() -> None:
    sessions = _sessions()
    sessions.create_session("s8")
    loop = IRFLoop(
        parser=FakeParser(
            _parser_output(_anchor_pref(tags=["文艺"]), confidence="low")
        ),
        planner=_planner_with([_poi("a")]),
        sessions=sessions,
    )
    events = asyncio.run(_collect(loop, "s8", " maybe 文艺? "))
    intent = next(e for e in events if e.type == "intent")
    assert intent.payload["confidence"] == "low"
    assert intent.payload["needs_clarification"] is True
    assert any(e.type == "token" for e in events)
    assert any(e.type == "feed" for e in events)
    print("low confidence still plans OK")


if __name__ == "__main__":
    test_single_round_event_sequence()
    test_state_persisted_after_round()
    test_two_rounds_round_increments()
    test_anchor_missing_not_persisted()
    test_empty_pool_not_persisted()
    test_invalid_empty_command()
    test_invalid_long_command()
    test_low_confidence_still_plans()
    print("ALL TESTS PASSED")
