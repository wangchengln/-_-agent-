#!/usr/bin/env python3
"""Tests for Parser I/O contracts (Module A)."""

import json
from pathlib import Path

from domain import (
    IRFSessionState,
    ParserInput,
    ParserOutput,
    PreferenceProfile,
    RecommendationFeed,
)


FIXTURE_FEED = Path(__file__).parent / "domain" / "fixtures" / "sample_feed.json"


def test_preference_to_parser_context_empty() -> None:
    profile = PreferenceProfile.empty()
    text = profile.to_parser_context()
    assert "[当前偏好 P_t]" in text
    assert "空白偏好" in text
    print("empty preference context OK")


def test_preference_to_parser_context_populated() -> None:
    feed = RecommendationFeed.model_validate_json(
        FIXTURE_FEED.read_text(encoding="utf-8")
    )
    text = feed.preference_snapshot.to_parser_context()
    assert "锚点:" in text
    assert "文艺" in text
    assert "半径5000m" in text
    assert "排除类别:商场" in text
    assert "不喜标签:人多" in text
    print("populated preference context OK:\n", text)


def test_feed_to_parser_context() -> None:
    feed = RecommendationFeed.model_validate_json(
        FIXTURE_FEED.read_text(encoding="utf-8")
    )
    text = feed.to_parser_context(max_items=3)
    assert "武康路历史文化名街" in text
    assert "西岸美术馆" in text
    assert "候选48个" in text
    assert "得分0.92" in text
    assert "raw" not in text
    print("feed context OK:\n", text)


def test_feed_to_parser_context_empty() -> None:
    feed = RecommendationFeed(round=1, items=[])
    text = feed.to_parser_context()
    assert "(空)" in text
    print("empty feed context OK")


def test_parser_input_from_irf_state() -> None:
    feed = RecommendationFeed.model_validate_json(
        FIXTURE_FEED.read_text(encoding="utf-8")
    )
    state = IRFSessionState(
        round=2,
        preference=feed.preference_snapshot,
        current_feed=feed,
        command_history=["上一轮命令"],
    )
    parser_input = state.build_parser_input("3公里内，别去商场")
    assert parser_input.round == 2
    assert parser_input.command == "3公里内，别去商场"
    assert "武康路" in parser_input.feed_context()
    assert "半径5000m" in parser_input.preference_context()
    assert "上一轮命令" in parser_input.history_context()
    print("ParserInput OK")


def test_parser_output_validation() -> None:
    output = ParserOutput(
        preference=PreferenceProfile.empty(),
        intent_summary="用户希望缩小搜索半径",
    )
    assert output.confidence == "high"

    try:
        ParserOutput(preference=PreferenceProfile.empty(), intent_summary="  ")
        raise AssertionError("expected validation error")
    except ValueError:
        pass
    print("ParserOutput validation OK")


def test_irf_session_round_trip() -> None:
    feed = RecommendationFeed.model_validate_json(
        FIXTURE_FEED.read_text(encoding="utf-8")
    )
    state = IRFSessionState(
        round=1,
        preference=feed.preference_snapshot,
        current_feed=feed,
    )
    blob = state.to_session_dict()
    restored = IRFSessionState.from_session_dict(blob)
    assert restored.round == state.round
    assert restored.preference.positive_soft.tags == state.preference.positive_soft.tags
    assert restored.current_feed is not None
    assert restored.current_feed.items[0].item.name == "武康路历史文化名街"
    print("session round-trip OK")


def test_irf_session_from_missing() -> None:
    state = IRFSessionState.from_session_dict(None)
    assert state.round == 1
    assert state.preference.positive_soft.tags == []
    print("from_session_dict(None) OK")


def test_apply_parser_output() -> None:
    feed = RecommendationFeed.model_validate_json(
        FIXTURE_FEED.read_text(encoding="utf-8")
    )
    state = IRFSessionState(round=1, preference=feed.preference_snapshot)

    new_pref = feed.preference_snapshot.model_copy(deep=True)
    new_pref.positive_hard.radius_m = 3000
    new_pref.positive_soft.tags = ["亲子"]
    output = ParserOutput(
        preference=new_pref,
        intent_summary="改为亲子出行，半径缩小到3公里",
    )

    next_state = state.apply_parser_output("3公里内，要亲子", output)
    assert next_state.round == 2
    assert next_state.preference.positive_hard.radius_m == 3000
    assert next_state.preference.positive_soft.tags == ["亲子"]
    assert next_state.command_history == ["3公里内，要亲子"]
    # Feed unchanged until Planner runs (Day 3)
    assert next_state.current_feed is None
    print("apply_parser_output OK")


def test_command_history_cap() -> None:
    state = IRFSessionState(
        command_history=[f"cmd{i}" for i in range(5)],
    )
    output = ParserOutput(
        preference=PreferenceProfile.empty(),
        intent_summary="测试",
    )
    next_state = state.apply_parser_output("cmd5", output)
    assert next_state.command_history == ["cmd1", "cmd2", "cmd3", "cmd4", "cmd5"]
    print("command history cap OK")


def test_parser_input_rejects_blank_command() -> None:
    try:
        ParserInput(command="   ", round=1)
        raise AssertionError("expected validation error")
    except ValueError:
        pass
    print("blank command rejection OK")


if __name__ == "__main__":
    test_preference_to_parser_context_empty()
    test_preference_to_parser_context_populated()
    test_feed_to_parser_context()
    test_feed_to_parser_context_empty()
    test_parser_input_from_irf_state()
    test_parser_output_validation()
    test_irf_session_round_trip()
    test_irf_session_from_missing()
    test_apply_parser_output()
    test_command_history_cap()
    test_parser_input_rejects_blank_command()
    print("ALL MODULE A TESTS PASSED")
