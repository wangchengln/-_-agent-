#!/usr/bin/env python3
"""Tests for recommend API SSE mapping — no network."""

from __future__ import annotations

from api.recommend import RecommendRequest, loop_event_to_sse
from recsys.errors import MAX_COMMAND_LENGTH
from recsys.loop import LoopEvent
from pydantic import ValidationError


def test_stage_maps_to_tool_start_end() -> None:
    start = loop_event_to_sse(
        LoopEvent(type="stage", payload={"name": "planner", "status": "start"})
    )
    assert start["event"] == "tool_start"
    assert "planner" in start["data"]

    end = loop_event_to_sse(
        LoopEvent(type="stage", payload={"name": "planner", "status": "end"})
    )
    assert end["event"] == "tool_end"
    print("stage -> tool_start/tool_end OK")


def test_feed_event_passthrough() -> None:
    frame = loop_event_to_sse(
        LoopEvent(type="feed", payload={"round": 1, "items": []})
    )
    assert frame["event"] == "feed"
    assert '"round": 1' in frame["data"]
    print("feed passthrough OK")


def test_recommend_request_rejects_empty_command() -> None:
    try:
        RecommendRequest(command="   ")
    except ValidationError as exc:
        assert "command must not be empty" in str(exc)
        print("request empty command rejected OK")
        return
    raise AssertionError("expected ValidationError")


def test_recommend_request_rejects_long_command() -> None:
    try:
        RecommendRequest(command="x" * (MAX_COMMAND_LENGTH + 1))
    except ValidationError as exc:
        assert str(MAX_COMMAND_LENGTH) in str(exc)
        print("request long command rejected OK")
        return
    raise AssertionError("expected ValidationError")


def test_error_event_passthrough() -> None:
    frame = loop_event_to_sse(
        LoopEvent(
            type="error",
            payload={
                "code": "anchor_missing",
                "message": "需要地点",
                "retry_hint": "例如上海",
                "session_id": "s1",
                "round": 1,
            },
        )
    )
    assert frame["event"] == "error"
    assert "retry_hint" in frame["data"]
    print("error passthrough OK")


if __name__ == "__main__":
    test_stage_maps_to_tool_start_end()
    test_feed_event_passthrough()
    test_recommend_request_rejects_empty_command()
    test_recommend_request_rejects_long_command()
    test_error_event_passthrough()
    print("ALL TESTS PASSED")
