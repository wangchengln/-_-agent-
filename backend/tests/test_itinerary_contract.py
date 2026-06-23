#!/usr/bin/env python3
"""Contract test: itinerary API payloads match frontend recommend-types.ts (Day 6.8)."""

from __future__ import annotations

import json
from pathlib import Path

from domain.itinerary import BuildItineraryResponse, WeekendItinerary
from domain.weather import WeatherSnapshot
from recsys.itinerary_errors import ITINERARY_ERROR_CODES

FIXTURE_ITINERARY = (
    Path(__file__).parent.parent / "domain" / "fixtures" / "sample_itinerary.json"
)

# frontend/src/lib/recommend-types.ts
ITINERARY_STOP_KEYS = frozenset(
    {
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
)

ITINERARY_LEG_KEYS = frozenset(
    {
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
)

WEEKEND_ITINERARY_KEYS = frozenset(
    {
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
)

BUILD_ITINERARY_RESPONSE_KEYS = frozenset({"itinerary", "warnings"})

TRANSPORT_MODES = frozenset({"walking", "driving", "transit"})


def _load_sample_itinerary() -> WeekendItinerary:
    return WeekendItinerary.model_validate_json(
        FIXTURE_ITINERARY.read_text(encoding="utf-8")
    )


def test_weekend_itinerary_payload_keys() -> None:
    itinerary = _load_sample_itinerary()
    payload = json.loads(itinerary.model_dump_json())
    assert set(payload.keys()) == WEEKEND_ITINERARY_KEYS
    assert payload["transport_mode"] in TRANSPORT_MODES
    assert len(payload["stops"]) >= 2
    print("WeekendItinerary payload keys OK")


def test_itinerary_stop_keys() -> None:
    itinerary = _load_sample_itinerary()
    for stop in itinerary.stops:
        keys = set(stop.model_dump(mode="json").keys())
        assert keys == ITINERARY_STOP_KEYS
        assert stop.lng is not None and stop.lat is not None
    print("ItineraryStop keys OK")


def test_itinerary_leg_keys() -> None:
    itinerary = _load_sample_itinerary()
    for leg in itinerary.legs:
        keys = set(leg.model_dump(mode="json").keys())
        assert keys == ITINERARY_LEG_KEYS
        assert leg.mode in TRANSPORT_MODES
        for point in leg.path:
            assert len(point) == 2
    print("ItineraryLeg keys OK")


def test_build_itinerary_response_shape() -> None:
    itinerary = _load_sample_itinerary()
    response = BuildItineraryResponse(itinerary=itinerary, warnings=["demo"])
    payload = json.loads(response.model_dump_json())
    assert set(payload.keys()) == BUILD_ITINERARY_RESPONSE_KEYS
    assert set(payload["itinerary"].keys()) == WEEKEND_ITINERARY_KEYS
    print("BuildItineraryResponse shape OK")


def test_itinerary_error_codes_align_with_frontend() -> None:
    frontend_codes = frozenset(
        {
            "no_feed",
            "poi_not_found",
            "missing_coords",
            "invalid_anchor_poi",
            "internal_error",
        }
    )
    assert ITINERARY_ERROR_CODES == frontend_codes
    print("itinerary error codes OK")


def test_itinerary_weather_nested_contract() -> None:
    itinerary = _load_sample_itinerary()
    assert itinerary.weather is not None
    weather_keys = set(itinerary.weather.model_dump(mode="json").keys())
    assert weather_keys == {
        "city",
        "adcode",
        "summary",
        "temperature",
        "is_rainy",
        "injected_rule",
        "fetched",
    }
    print("itinerary weather nested contract OK")


def test_weather_snapshot_standalone() -> None:
    snap = WeatherSnapshot(
        city="上海",
        adcode="310100",
        summary="晴",
        temperature="26",
        is_rainy=False,
        injected_rule=None,
        fetched=True,
    )
    assert set(snap.model_dump(mode="json").keys()) == {
        "city",
        "adcode",
        "summary",
        "temperature",
        "is_rainy",
        "injected_rule",
        "fetched",
    }
    print("WeatherSnapshot standalone OK")


if __name__ == "__main__":
    test_weekend_itinerary_payload_keys()
    test_itinerary_stop_keys()
    test_itinerary_leg_keys()
    test_build_itinerary_response_shape()
    test_itinerary_error_codes_align_with_frontend()
    test_itinerary_weather_nested_contract()
    test_weather_snapshot_standalone()
    print("ALL ITINERARY CONTRACT TESTS PASSED")
