#!/usr/bin/env python3
"""Day 6 integration: feed → weather → itinerary persistence (Day 6.8)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from domain import IRFSessionState, RecommendationFeed
from domain.itinerary import BuildItineraryRequest
from domain.types import GeoLocation
from domain.weather import WeatherSnapshot
from graph.session_manager import SessionManager
from recsys.itinerary_planner import ItineraryPlanner
from recsys.loop import feed_event, feed_item_payload
from tools.amap_client import RoutePlan

FIXTURE_FEED = Path(__file__).parent.parent / "domain" / "fixtures" / "sample_feed.json"

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

WEATHER_KEYS = frozenset(
    {
        "city",
        "adcode",
        "summary",
        "temperature",
        "is_rainy",
        "injected_rule",
        "fetched",
    }
)


class FakeRouteClient:
    def plan_walking_route(
        self, origin: GeoLocation, destination: GeoLocation
    ) -> RoutePlan:
        return RoutePlan(
            mode="walking",
            distance_m=1500,
            duration_s=800,
            origin=origin,
            destination=destination,
            steps=[],
        )


def test_feed_items_include_coordinates_for_map() -> None:
    feed = RecommendationFeed.model_validate_json(
        FIXTURE_FEED.read_text(encoding="utf-8")
    )
    preference = feed.preference_snapshot
    for scored in feed.items:
        payload = feed_item_payload(scored, preference)
        assert set(payload.keys()) == FEED_ITEM_KEYS
        assert payload["lng"] is not None and payload["lat"] is not None
    print("feed coordinates for map OK")


def test_feed_event_with_weather_round_trip() -> None:
    feed = RecommendationFeed.model_validate_json(
        FIXTURE_FEED.read_text(encoding="utf-8")
    )
    feed.weather = WeatherSnapshot(
        city="上海",
        adcode="310100",
        summary="小雨",
        temperature="18",
        is_rainy=True,
        injected_rule="venue_type=indoor",
        fetched=True,
    )
    preference = feed.preference_snapshot
    event = feed_event(feed, preference)
    serialized = json.loads(json.dumps(event.payload, ensure_ascii=False))

    assert serialized["weather"] is not None
    assert set(serialized["weather"].keys()) == WEATHER_KEYS
    assert serialized["weather"]["is_rainy"] is True
    assert serialized["weather"]["injected_rule"] == "venue_type=indoor"
    print("feed + weather SSE round-trip OK")


def test_session_feed_to_itinerary_flow() -> None:
    """Simulates: IRF feed stored → user selects POIs → planner persists itinerary."""
    feed = RecommendationFeed.model_validate_json(
        FIXTURE_FEED.read_text(encoding="utf-8")
    )
    feed.weather = WeatherSnapshot(
        city="上海",
        adcode="310100",
        summary="晴",
        temperature="26",
        is_rainy=False,
        fetched=True,
    )

    with tempfile.TemporaryDirectory() as tmp:
        session_id = "day6-flow"
        manager = SessionManager()
        manager.initialize(Path(tmp))
        manager.create_session(session_id)
        manager.save_irf_state(session_id, IRFSessionState.empty().with_feed(feed))

        planner = ItineraryPlanner(sessions=manager, amap_client=FakeRouteClient())
        poi_ids = feed.poi_ids[:3]
        response = planner.build(
            BuildItineraryRequest(
                session_id=session_id,
                poi_ids=poi_ids,
                transport_mode="walking",
            )
        )

        itinerary = response.itinerary
        assert itinerary.session_id == session_id
        assert set(itinerary.poi_ids) == set(poi_ids)
        assert itinerary.stop_count == 3
        assert len(itinerary.legs) == 2
        assert all(s.lng is not None and s.lat is not None for s in itinerary.stops)
        assert all(len(leg.path) >= 0 for leg in itinerary.legs)

        reloaded = manager.get_irf_state(session_id)
        assert reloaded.current_itinerary is not None
        assert set(reloaded.current_itinerary.poi_ids) == set(poi_ids)

        api_json = json.loads(response.model_dump_json())
        assert "itinerary" in api_json or "stops" in api_json
        print("session feed → itinerary flow OK")


def test_itinerary_response_json_matches_frontend_types() -> None:
    feed = RecommendationFeed.model_validate_json(
        FIXTURE_FEED.read_text(encoding="utf-8")
    )
    with tempfile.TemporaryDirectory() as tmp:
        manager = SessionManager()
        manager.initialize(Path(tmp))
        manager.create_session("json-check")
        manager.save_irf_state("json-check", IRFSessionState.empty().with_feed(feed))
        planner = ItineraryPlanner(sessions=manager, amap_client=FakeRouteClient())
        response = planner.build(
            BuildItineraryRequest(
                session_id="json-check",
                poi_ids=feed.poi_ids[:2],
            )
        )
        payload = json.loads(response.model_dump_json())
        itinerary = payload["itinerary"]
        required_top = {
            "session_id",
            "transport_mode",
            "stops",
            "legs",
            "total_distance_m",
            "total_travel_min",
            "total_dwell_min",
            "warnings",
            "generated_at",
        }
        assert required_top.issubset(set(itinerary.keys()))
        assert itinerary["transport_mode"] in {"walking", "driving", "transit"}
        print("itinerary JSON frontend-compatible OK")


if __name__ == "__main__":
    test_feed_items_include_coordinates_for_map()
    test_feed_event_with_weather_round_trip()
    test_session_feed_to_itinerary_flow()
    test_itinerary_response_json_matches_frontend_types()
    print("ALL DAY 6 INTEGRATION TESTS PASSED")
