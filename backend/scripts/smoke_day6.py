#!/usr/bin/env python3
"""Day 6 end-to-end smoke: recommend SSE → feed contract → POST /api/itinerary (Day 6.8).

Requires backend running on 127.0.0.1:8002 with AMAP_WEB_SERVICE_KEY configured.

  cd backend
  uvicorn app:app --host 0.0.0.0 --port 8002

  python scripts/smoke_day6.py
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

from scripts.smoke_recommend_stream import (  # noqa: E402
    BASE_URL,
    FEED_ITEM_KEYS,
    FEED_PAYLOAD_KEYS,
    _assert_feed_contract,
    _parse_sse,
    _stream_recommend,
    _wait_for_server,
)

SESSION_ID = f"smoke-day6-{int(time.time())}"

WEATHER_KEYS = {
    "city",
    "adcode",
    "summary",
    "temperature",
    "is_rainy",
    "injected_rule",
    "fetched",
}

ITINERARY_STOP_KEYS = {
    "order",
    "poi_id",
    "name",
    "type",
    "lng",
    "lat",
    "address",
    "arrive_at",
    "leave_at",
    "dwell_min",
}

ITINERARY_LEG_KEYS = {
    "from_poi_id",
    "to_poi_id",
    "mode",
    "distance_m",
    "duration_s",
    "depart_at",
    "arrive_at",
    "path",
    "estimated",
}

WEEKEND_ITINERARY_KEYS = {
    "session_id",
    "round",
    "anchor",
    "transport_mode",
    "day_start",
    "day_end",
    "stops",
    "legs",
    "total_distance_m",
    "total_travel_min",
    "total_dwell_min",
    "weather",
    "warnings",
    "generated_at",
}


def _assert_weather_contract(weather: dict | None) -> None:
    if weather is None:
        print("weather: null (anchor missing or fetch skipped) — OK")
        return
    missing = WEATHER_KEYS - set(weather.keys())
    assert not missing, f"weather missing keys: {missing}"
    assert isinstance(weather["is_rainy"], bool)
    print(f"weather OK: {weather.get('city')} {weather.get('summary')!r} "
          f"rainy={weather.get('is_rainy')}")


def _post_itinerary(
    session_id: str,
    poi_ids: list[str],
    *,
    transport_mode: str = "walking",
) -> dict:
    payload = json.dumps(
        {
            "session_id": session_id,
            "poi_ids": poi_ids,
            "transport_mode": transport_mode,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/itinerary",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _assert_itinerary_contract(body: dict, *, min_stops: int = 2) -> None:
    assert set(body.keys()) == {"itinerary", "warnings"}, (
        f"itinerary response keys: {sorted(body.keys())}"
    )
    itinerary = body["itinerary"]
    missing = WEEKEND_ITINERARY_KEYS - set(itinerary.keys())
    assert not missing, f"itinerary missing keys: {missing}"
    assert len(itinerary["stops"]) >= min_stops
    assert itinerary["transport_mode"] in {"walking", "driving", "transit"}

    for stop in itinerary["stops"]:
        missing_stop = ITINERARY_STOP_KEYS - set(stop.keys())
        assert not missing_stop, f"stop missing keys: {missing_stop}"
        assert stop["lng"] is not None and stop["lat"] is not None

    for leg in itinerary["legs"]:
        missing_leg = ITINERARY_LEG_KEYS - set(leg.keys())
        assert not missing_leg, f"leg missing keys: {missing_leg}"

    print(
        f"itinerary OK: {len(itinerary['stops'])} stops, "
        f"{itinerary['total_travel_min']} min travel, "
        f"{itinerary['total_distance_m']} m"
    )


def main() -> int:
    _wait_for_server()
    print(f"session={SESSION_ID}")

    # ── Step 1: IRF recommend round ─────────────────────
    events = _stream_recommend(
        "上海周末想找个文艺的地方，不要太远",
        session_id=SESSION_ID,
    )
    names = [n for n, _ in events]
    assert "feed" in names, "missing feed event"
    feed = next(data for name, data in events if name == "feed")
    _assert_feed_contract(feed, expected_round=1)
    _assert_weather_contract(feed.get("weather"))

    for item in feed["items"]:
        assert item["lng"] is not None and item["lat"] is not None, (
            f"feed item {item['poi_id']} missing coordinates"
        )
    print(f"feed OK: {len(feed['items'])} items with lng/lat")

    # ── Step 2: Build weekend itinerary from selected POIs ──
    poi_ids = [item["poi_id"] for item in feed["items"][:3]]
    assert len(poi_ids) >= 2, "need at least 2 POIs for itinerary"
    body = _post_itinerary(SESSION_ID, poi_ids, transport_mode="walking")
    _assert_itinerary_contract(body, min_stops=len(poi_ids))

    # ── Step 3: Error branch — unknown POI ────────────────
    err_session = f"{SESSION_ID}-err"
    _stream_recommend("杭州西湖边适合散步", session_id=err_session)
    try:
        _post_itinerary(err_session, ["not-in-feed-a", "not-in-feed-b"])
    except urllib.error.HTTPError as exc:
        assert exc.code == 400, f"expected 400, got {exc.code}"
        detail = json.loads(exc.read().decode("utf-8"))
        err_body = detail.get("detail", detail)
        assert err_body.get("code") == "poi_not_found", err_body
        print(f"itinerary error branch OK: code={err_body.get('code')!r}")
    else:
        raise AssertionError("expected 400 for poi_not_found")

    print("\nALL DAY 6 SMOKE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
