#!/usr/bin/env python3
"""Tests for weekend itinerary domain models (Day 6.3)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from domain import (
    BuildItineraryRequest,
    BuildItineraryResponse,
    IRFSessionState,
    WeekendItinerary,
)
from domain.itinerary import ItineraryLeg, ItineraryStop
from graph.session_manager import SessionManager

FIXTURE_ITINERARY = (
    Path(__file__).parent.parent / "domain" / "fixtures" / "sample_itinerary.json"
)


def test_sample_itinerary_fixture_round_trip() -> None:
    raw = FIXTURE_ITINERARY.read_text(encoding="utf-8")
    itinerary = WeekendItinerary.model_validate_json(raw)
    assert itinerary.stop_count == 3
    assert itinerary.poi_ids == ["B001A0LXYZ", "B002B1MNPQ", "B003C2RSTU"]
    assert len(itinerary.legs) == 2
    assert itinerary.total_distance_m == 5000
    assert itinerary.weather is not None
    assert itinerary.weather.summary == "晴"

    serialized = json.loads(itinerary.model_dump_json())
    restored = WeekendItinerary.model_validate(serialized)
    assert restored.to_timeline_context() == itinerary.to_timeline_context()
    print("sample_itinerary fixture OK")


def test_build_itinerary_request_validation() -> None:
    req = BuildItineraryRequest(
        session_id="s1",
        poi_ids=["a", "b", "c"],
        transport_mode="driving",
        day_start="10:00",
        day_end="20:00",
    )
    assert req.poi_ids == ["a", "b", "c"]
    assert req.transport_mode == "driving"
    print("BuildItineraryRequest OK")


def test_build_itinerary_request_rejects_invalid_input() -> None:
    with pytest.raises(ValueError, match="unique"):
        BuildItineraryRequest(poi_ids=["a", "a"])

    with pytest.raises(ValueError, match="day_end"):
        BuildItineraryRequest(poi_ids=["a", "b"], day_start="18:00", day_end="09:00")

    with pytest.raises(ValueError, match="at most"):
        BuildItineraryRequest(poi_ids=["1", "2", "3", "4", "5", "6"])
    print("BuildItineraryRequest validation OK")


def test_itinerary_stop_dwell_consistency() -> None:
    stop = ItineraryStop(
        order=1,
        poi_id="p1",
        name="测试点",
        arrive_at="09:30",
        leave_at="10:30",
        dwell_min=60,
    )
    assert stop.has_coordinates is False

    with pytest.raises(ValueError, match="dwell_min"):
        ItineraryStop(
            order=1,
            poi_id="p1",
            name="测试点",
            arrive_at="09:30",
            leave_at="10:30",
            dwell_min=45,
        )
    print("ItineraryStop validation OK")


def test_weekend_itinerary_leg_chain_validation() -> None:
    stop_a = ItineraryStop(
        order=1,
        poi_id="a",
        name="A",
        arrive_at="09:30",
        leave_at="10:30",
        dwell_min=60,
    )
    stop_b = ItineraryStop(
        order=2,
        poi_id="b",
        name="B",
        arrive_at="10:45",
        leave_at="11:45",
        dwell_min=60,
    )
    leg = ItineraryLeg(
        from_poi_id="a",
        to_poi_id="b",
        mode="walking",
        distance_m=1200,
        duration_s=900,
        depart_at="10:30",
        arrive_at="10:45",
    )
    itinerary = WeekendItinerary(
        session_id="s1",
        day_start="09:30",
        day_end="21:00",
        stops=[stop_a, stop_b],
        legs=[leg],
        total_distance_m=1200,
        total_travel_min=15,
        total_dwell_min=120,
    )
    assert "A" in itinerary.to_timeline_context()

    with pytest.raises(ValueError, match="must connect stop"):
        WeekendItinerary(
            session_id="s1",
            day_start="09:30",
            day_end="21:00",
            stops=[stop_a, stop_b],
            legs=[
                ItineraryLeg(
                    from_poi_id="x",
                    to_poi_id="b",
                    mode="walking",
                    distance_m=1,
                    duration_s=60,
                    depart_at="10:30",
                    arrive_at="10:45",
                )
            ],
        )
    print("WeekendItinerary leg chain OK")


def test_build_itinerary_response_shape() -> None:
    itinerary = WeekendItinerary.model_validate_json(
        FIXTURE_ITINERARY.read_text(encoding="utf-8")
    )
    response = BuildItineraryResponse(
        itinerary=itinerary,
        warnings=["时间偏紧，建议减少 1 个站点"],
    )
    assert response.warnings == ["时间偏紧，建议减少 1 个站点"]
    assert response.itinerary.stop_count == 3
    print("BuildItineraryResponse OK")


def test_irf_state_persists_current_itinerary() -> None:
    itinerary = WeekendItinerary.model_validate_json(
        FIXTURE_ITINERARY.read_text(encoding="utf-8")
    )
    state = IRFSessionState.empty().with_itinerary(itinerary)
    assert state.current_itinerary is not None
    assert state.current_itinerary.poi_ids[0] == "B001A0LXYZ"

    payload = state.to_session_dict()
    restored = IRFSessionState.from_session_dict(payload)
    assert restored.current_itinerary is not None
    assert restored.current_itinerary.session_id == "sample-session"
    print("IRFSessionState itinerary persistence OK")


def test_session_manager_round_trip_itinerary() -> None:
    itinerary = WeekendItinerary.model_validate_json(
        FIXTURE_ITINERARY.read_text(encoding="utf-8")
    )
    with tempfile.TemporaryDirectory() as tmp:
        manager = SessionManager()
        manager.initialize(Path(tmp))
        manager.create_session("itinerary-session")
        manager.save_irf_state(
            "itinerary-session",
            IRFSessionState.empty().with_itinerary(itinerary),
        )
        reloaded = manager.get_irf_state("itinerary-session")
        assert reloaded.current_itinerary is not None
        assert reloaded.current_itinerary.stop_count == 3
    print("session manager itinerary round-trip OK")


if __name__ == "__main__":
    test_sample_itinerary_fixture_round_trip()
    test_build_itinerary_request_validation()
    test_build_itinerary_request_rejects_invalid_input()
    test_itinerary_stop_dwell_consistency()
    test_weekend_itinerary_leg_chain_validation()
    test_build_itinerary_response_shape()
    test_irf_state_persists_current_itinerary()
    test_session_manager_round_trip_itinerary()
    print("ALL ITINERARY TESTS PASSED")
