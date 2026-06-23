#!/usr/bin/env python3
"""Tests for POST /api/itinerary HTTP handler (Day 6.8)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.itinerary import router, run_build_itinerary
from domain import IRFSessionState, RecommendationFeed
from domain.itinerary import BuildItineraryRequest
from domain.types import GeoLocation
from graph.session_manager import SessionManager
from recsys.itinerary_planner import ItineraryPlanner
from tools.amap_client import RoutePlan

FIXTURE_FEED = Path(__file__).parent.parent / "domain" / "fixtures" / "sample_feed.json"


class FakeRouteClient:
    def plan_walking_route(
        self, origin: GeoLocation, destination: GeoLocation
    ) -> RoutePlan:
        return RoutePlan(
            mode="walking",
            distance_m=1000,
            duration_s=720,
            origin=origin,
            destination=destination,
            steps=[],
        )

    def plan_driving_route(
        self, origin: GeoLocation, destination: GeoLocation
    ) -> RoutePlan:
        return RoutePlan(
            mode="driving",
            distance_m=3000,
            duration_s=480,
            origin=origin,
            destination=destination,
            steps=[],
        )

    def plan_transit_route(
        self,
        origin: GeoLocation,
        destination: GeoLocation,
        *,
        city: str,
        strategy: int = 0,
    ) -> RoutePlan:
        return RoutePlan(
            mode="transit",
            distance_m=2500,
            duration_s=900,
            origin=origin,
            destination=destination,
            steps=[],
        )


def _planner_with_feed(tmp: Path) -> tuple[ItineraryPlanner, RecommendationFeed]:
    feed = RecommendationFeed.model_validate_json(
        FIXTURE_FEED.read_text(encoding="utf-8")
    )
    manager = SessionManager()
    manager.initialize(tmp)
    manager.create_session("api-test")
    manager.save_irf_state("api-test", IRFSessionState.empty().with_feed(feed))
    planner = ItineraryPlanner(sessions=manager, amap_client=FakeRouteClient())
    return planner, feed


class TestItineraryApiHandler(unittest.IsolatedAsyncioTestCase):
    async def test_build_itinerary_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            planner, feed = _planner_with_feed(Path(tmp))
            request = BuildItineraryRequest(
                session_id="api-test",
                poi_ids=feed.poi_ids[:2],
                transport_mode="walking",
            )
            response = await run_build_itinerary(request, planner=planner)
            self.assertEqual(response.itinerary.stop_count, 2)
            self.assertEqual(len(response.itinerary.legs), 1)
            self.assertIsInstance(response.warnings, list)
            print("build_itinerary handler OK")

    async def test_build_itinerary_no_feed_returns_400(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = SessionManager()
            manager.initialize(Path(tmp))
            manager.create_session("empty")
            planner = ItineraryPlanner(
                sessions=manager, amap_client=FakeRouteClient()
            )
            request = BuildItineraryRequest(
                session_id="empty",
                poi_ids=["B001A0LXYZ", "B002B1MNPQ"],
            )
            with pytest.raises(HTTPException) as exc_info:
                await run_build_itinerary(request, planner=planner)
            self.assertEqual(exc_info.value.status_code, 400)
            detail = exc_info.value.detail
            assert isinstance(detail, dict)
            self.assertEqual(detail["code"], "no_feed")
            self.assertIn("message", detail)
            print("no_feed HTTP 400 OK")

    async def test_build_itinerary_poi_not_found_returns_400(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            planner, feed = _planner_with_feed(Path(tmp))
            request = BuildItineraryRequest(
                session_id="api-test",
                poi_ids=["missing-a", "missing-b"],
            )
            with pytest.raises(HTTPException) as exc_info:
                await run_build_itinerary(request, planner=planner)
            self.assertEqual(exc_info.value.status_code, 400)
            detail = exc_info.value.detail
            assert isinstance(detail, dict)
            self.assertEqual(detail["code"], "poi_not_found")
            print("poi_not_found HTTP 400 OK")


class TestItineraryApiRouter(unittest.TestCase):
    def test_post_itinerary_via_test_client(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            planner, feed = _planner_with_feed(Path(tmp))
            import api.itinerary as itinerary_api

            original = itinerary_api.itinerary_planner
            itinerary_api.itinerary_planner = planner
            try:
                app = FastAPI()
                app.include_router(router, prefix="/api")
                client = TestClient(app)
                resp = client.post(
                    "/api/itinerary",
                    json={
                        "session_id": "api-test",
                        "poi_ids": feed.poi_ids[:2],
                        "transport_mode": "walking",
                    },
                )
                self.assertEqual(resp.status_code, 200, resp.text)
                body = resp.json()
                self.assertIn("itinerary", body)
                self.assertIn("warnings", body)
                self.assertEqual(len(body["itinerary"]["stops"]), 2)
                self.assertEqual(body["itinerary"]["transport_mode"], "walking")
                print("POST /api/itinerary TestClient OK")
            finally:
                itinerary_api.itinerary_planner = original

    def test_post_itinerary_validation_error(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api")
        client = TestClient(app)
        resp = client.post(
            "/api/itinerary",
            json={"session_id": "s1", "poi_ids": ["only-one"]},
        )
        self.assertEqual(resp.status_code, 422)
        print("POST /api/itinerary 422 validation OK")


if __name__ == "__main__":
    unittest.main()
