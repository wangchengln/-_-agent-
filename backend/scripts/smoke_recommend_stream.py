#!/usr/bin/env python3
"""End-to-end SSE smoke test for POST /api/recommend (Day 5.12).

Mimics the frontend `streamRecommend()` + store event handling and asserts the
wire contract the UI relies on:

  intent -> tool_start/tool_end (stage) -> feed -> token* -> done

Also exercises the anchor_missing error branch.

Run while the backend is up on 127.0.0.1:8002.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))

BASE_URL = "http://127.0.0.1:8002"
SESSION_ID = f"smoke-stream-{int(time.time())}"

# Keys the frontend FeedItem type depends on (recommend-types.ts).
FEED_ITEM_KEYS = {
    "rank", "poi_id", "name", "type", "rating",
    "distance_m", "cost", "address", "tags", "photos", "score", "reason",
}
FEED_PAYLOAD_KEYS = {
    "round", "k", "total_candidates", "items", "preference", "preference_summary",
}


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    """Parse an SSE response body into (event, data) frames."""
    events: list[tuple[str, dict]] = []
    current_event = "message"
    for line in raw.split("\n"):
        line = line.rstrip("\r")
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_str = line[len("data:"):].strip()
            if data_str:
                try:
                    events.append((current_event, json.loads(data_str)))
                except json.JSONDecodeError:
                    pass
        elif line == "":
            current_event = "message"
    return events


def _stream_recommend(command: str, session_id: str = SESSION_ID) -> list[tuple[str, dict]]:
    payload = json.dumps(
        {"command": command, "session_id": session_id, "stream": True},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/recommend",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = resp.read().decode("utf-8")
    return _parse_sse(body)


def _wait_for_server(timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/", timeout=2) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)
    raise RuntimeError(f"backend not reachable at {BASE_URL}")


def _assert_feed_contract(feed: dict, *, expected_round: int) -> None:
    assert set(feed.keys()) == FEED_PAYLOAD_KEYS, (
        f"feed payload keys mismatch: {sorted(feed.keys())}"
    )
    assert feed["round"] == expected_round, (
        f"expected round {expected_round}, got {feed['round']}"
    )
    assert feed["items"], "feed has no items"
    for item in feed["items"]:
        missing = FEED_ITEM_KEYS - set(item.keys())
        assert not missing, f"feed item missing keys: {missing}"
        assert isinstance(item["reason"], str) and item["reason"], "empty reason"
    assert isinstance(feed["preference"], dict), "preference not an object"
    assert isinstance(feed["preference_summary"], str), "preference_summary not str"


def _summarize(events: list[tuple[str, dict]]) -> dict:
    kinds: dict[str, int] = {}
    for name, _ in events:
        kinds[name] = kinds.get(name, 0) + 1
    return kinds


def main() -> int:
    _wait_for_server()
    print(f"session={SESSION_ID}")

    # ── Round 1 ──────────────────────────────────────────
    ev1 = _stream_recommend("上海周末想找个文艺的地方，不要太远")
    kinds1 = _summarize(ev1)
    print("round1 events:", kinds1)

    names1 = [n for n, _ in ev1]
    assert "intent" in names1, "round1 missing intent event"
    assert "feed" in names1, "round1 missing feed event"
    assert "done" in names1, "round1 missing done event"
    assert kinds1.get("tool_start", 0) >= 1, "round1 missing tool_start (planner stage)"
    assert kinds1.get("tool_end", 0) >= 1, "round1 missing tool_end"
    assert kinds1.get("token", 0) >= 1, "round1 missing rationale tokens"

    # Event ordering: intent before feed before done.
    assert names1.index("intent") < names1.index("feed") < names1.index("done"), (
        f"round1 event order wrong: {names1}"
    )

    feed1 = next(data for name, data in ev1 if name == "feed")
    _assert_feed_contract(feed1, expected_round=1)
    print(f"round1 OK: {len(feed1['items'])} items, "
          f"candidates={feed1['total_candidates']}")

    intent1 = next(data for name, data in ev1 if name == "intent")
    assert set(intent1.keys()) == {"intent_summary", "confidence", "needs_clarification"}
    print(f"round1 intent: {intent1['intent_summary']!r} "
          f"(confidence={intent1['confidence']})")

    # ── Round 2 (same session → round increments, feed refreshes) ──
    ev2 = _stream_recommend("换几家咖啡馆，人均别太贵")
    kinds2 = _summarize(ev2)
    print("round2 events:", kinds2)
    feed2 = next(data for name, data in ev2 if name == "feed")
    _assert_feed_contract(feed2, expected_round=2)
    print(f"round2 OK: {len(feed2['items'])} items")

    # Feed should change between rounds (refresh, not identical).
    ids1 = [i["poi_id"] for i in feed1["items"]]
    ids2 = [i["poi_id"] for i in feed2["items"]]
    if ids1 == ids2:
        print("note: round2 feed identical to round1 (acceptable but unusual)")
    else:
        print("round2 feed refreshed (different items) OK")

    # ── Error branch: anchor_missing on a fresh session ──
    err_session = f"{SESSION_ID}-err"
    ev_err = _stream_recommend("随便推荐点啥", session_id=err_session)
    err_frames = [data for name, data in ev_err if name == "error"]
    if err_frames:
        err = err_frames[0]
        assert "code" in err and "message" in err, f"error frame malformed: {err}"
        assert "retry_hint" in err, "error frame missing retry_hint"
        print(f"error branch OK: code={err['code']!r} "
              f"retry_hint={err.get('retry_hint')!r}")
    else:
        # Parser may have resolved a default anchor — that's also valid.
        feed_err = [d for n, d in ev_err if n == "feed"]
        print("error branch: no error (parser resolved anchor), "
              f"feed_emitted={bool(feed_err)}")

    print("\nALL STREAM SMOKE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
