#!/usr/bin/env python3
"""Contract test: backend SSE payloads match frontend recommend-types.ts expectations."""

from __future__ import annotations

import json
from pathlib import Path

from domain.feed import RecommendationFeed
from domain.preference import PreferenceProfile
from recsys.errors import ERROR_CODES
from recsys.loop import (
    done_event,
    error_event,
    feed_event,
    feed_item_payload,
    intent_event,
)

FIXTURE_FEED = Path(__file__).parent.parent / "domain" / "fixtures" / "sample_feed.json"

# Keys expected by frontend/src/lib/recommend-types.ts
FEED_ITEM_KEYS = frozenset(
    {
        "rank",
        "poi_id",
        "name",
        "type",
        "lng",
        "lat",
        "rating",
        "distance_m",
        "cost",
        "address",
        "tags",
        "photos",
        "score",
        "reason",
    }
)

FEED_PAYLOAD_KEYS = frozenset(
    {
        "round",
        "k",
        "total_candidates",
        "items",
        "preference",
        "preference_summary",
        "weather",
    }
)

PREFERENCE_KEYS = frozenset(
    {
        "version",
        "anchor",
        "positive_hard",
        "positive_soft",
        "negative_hard",
        "negative_soft",
        "updated_at",
        "source_command",
    }
)


def _load_sample_feed() -> RecommendationFeed:
    return RecommendationFeed.model_validate_json(FIXTURE_FEED.read_text(encoding="utf-8"))


def test_feed_item_payload_keys() -> None:
    feed = _load_sample_feed()
    preference = feed.preference_snapshot
    for scored in feed.items:
        payload = feed_item_payload(scored, preference)
        assert set(payload.keys()) == FEED_ITEM_KEYS
        assert isinstance(payload["reason"], str) and payload["reason"]
        assert payload["poi_id"] == scored.item.id
        assert payload["lng"] == scored.item.location.lng
        assert payload["lat"] == scored.item.location.lat
    print("feed_item_payload keys OK")


def test_feed_event_payload_keys() -> None:
    feed = _load_sample_feed()
    preference = feed.preference_snapshot
    event = feed_event(feed, preference)
    assert event.type == "feed"
    assert set(event.payload.keys()) == FEED_PAYLOAD_KEYS
    assert len(event.payload["items"]) == len(feed.items)
    assert set(event.payload["preference"].keys()) == PREFERENCE_KEYS
    assert isinstance(event.payload["preference_summary"], str)
    assert event.payload["weather"] is None
    print("feed_event payload keys OK")


def test_intent_event_payload() -> None:
    event = intent_event("上海文艺周末", "high", needs_clarification=False)
    assert event.type == "intent"
    assert set(event.payload.keys()) == {
        "intent_summary",
        "confidence",
        "needs_clarification",
    }
    print("intent_event payload OK")


def test_error_event_codes_align_with_frontend() -> None:
    for code in ERROR_CODES:
        event = error_event(code, session_id="s1", round_index=1)
        payload = event.payload
        assert payload["code"] == code
        assert "message" in payload
        assert "retry_hint" in payload
    print("error_event codes OK")


def test_done_event_payload() -> None:
    event = done_event("session-1", 2)
    assert event.type == "done"
    assert event.payload == {"session_id": "session-1", "round": 2}
    print("done_event payload OK")


def test_sample_feed_serializes_for_frontend() -> None:
    """Ensure fixture round-trips through feed_event JSON without loss."""
    feed = _load_sample_feed()
    preference = PreferenceProfile.model_validate(
        feed.preference_snapshot.model_dump(mode="json")
    )
    event = feed_event(feed, preference)
    serialized = json.loads(json.dumps(event.payload, ensure_ascii=False))
    assert serialized["round"] == feed.round
    assert serialized["k"] == feed.k
    assert len(serialized["items"]) == 3
    assert serialized["items"][0]["name"] == "武康路历史文化名街"
    assert serialized["items"][0]["lng"] == 121.4374
    assert serialized["items"][0]["lat"] == 31.2043
    print("sample_feed JSON round-trip OK")


if __name__ == "__main__":
    test_feed_item_payload_keys()
    test_feed_event_payload_keys()
    test_intent_event_payload()
    test_error_event_codes_align_with_frontend()
    test_done_event_payload()
    test_sample_feed_serializes_for_frontend()
    print("ALL CONTRACT TESTS PASSED")
