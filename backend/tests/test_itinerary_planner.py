#!/usr/bin/env python3
"""Tests for ItineraryPlanner (Day 6.4)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from domain import IRFSessionState, RecommendationFeed
from domain.itinerary import BuildItineraryRequest
from domain.types import GeoLocation
from graph.session_manager import SessionManager
from recsys.itinerary_errors import ItineraryPlannerError
from recsys.itinerary_planner import ItineraryPlanner, estimate_dwell_min
from tools.amap_client import RoutePlan

FIXTURE_FEED = Path(__file__).parent.parent / "domain" / "fixtures" / "sample_feed.json"


class FakeRouteClient:
    def plan_walking_route(self, origin: GeoLocation, destination: GeoLocation) -> RoutePlan:
        return RoutePlan(
            mode="walking",
            distance_m=1200,
            duration_s=900,
            origin=origin,
            destination=destination,
            steps=[],
        )

    def plan_driving_route(self, origin: GeoLocation, destination: GeoLocation) -> RoutePlan:
        return RoutePlan(
            mode="driving",
            distance_m=5000,
            duration_s=600,
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
            distance_m=4000,
            duration_s=1200,
            origin=origin,
            destination=destination,
            steps=[],
        )


def _manager_with_feed(tmp: Path) -> tuple[SessionManager, RecommendationFeed]:
    feed = RecommendationFeed.model_validate_json(
        FIXTURE_FEED.read_text(encoding="utf-8")
    )
    manager = SessionManager()
    manager.initialize(tmp)
    manager.create_session("plan-test")
    manager.save_irf_state("plan-test", IRFSessionState.empty().with_feed(feed))
    return manager, feed


class TestItineraryPlanner(unittest.TestCase):
    def test_build_three_stop_itinerary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager, feed = _manager_with_feed(Path(tmp))
            planner = ItineraryPlanner(
                sessions=manager,
                amap_client=FakeRouteClient(),
            )
            response = planner.build(
                BuildItineraryRequest(
                    session_id="plan-test",
                    poi_ids=feed.poi_ids[:3],
                    transport_mode="walking",
                )
            )
            itinerary = response.itinerary
            self.assertEqual(itinerary.stop_count, 3)
            self.assertEqual(len(itinerary.legs), 2)
            self.assertGreater(itinerary.total_dwell_min, 0)
            self.assertGreater(itinerary.total_travel_min, 0)

            reloaded = manager.get_irf_state("plan-test")
            self.assertIsNotNone(reloaded.current_itinerary)
            self.assertEqual(reloaded.current_itinerary.poi_ids, itinerary.poi_ids)
            print("three-stop itinerary OK")

    def test_nearest_neighbor_ordering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager, feed = _manager_with_feed(Path(tmp))
            planner = ItineraryPlanner(
                sessions=manager,
                amap_client=FakeRouteClient(),
            )
            response = planner.build(
                BuildItineraryRequest(
                    session_id="plan-test",
                    poi_ids=feed.poi_ids[:3],
                    anchor_poi_id="B001A0LXYZ",
                )
            )
            self.assertEqual(response.itinerary.stops[0].poi_id, "B001A0LXYZ")
            print("anchor_poi_id ordering OK")

    def test_poi_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager, _ = _manager_with_feed(Path(tmp))
            planner = ItineraryPlanner(
                sessions=manager,
                amap_client=FakeRouteClient(),
            )
            with self.assertRaises(ItineraryPlannerError) as ctx:
                planner.build(
                    BuildItineraryRequest(
                        session_id="plan-test",
                        poi_ids=["missing-a", "missing-b"],
                    )
                )
            self.assertEqual(ctx.exception.code, "poi_not_found")
            print("poi_not_found OK")

    def test_no_feed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = SessionManager()
            manager.initialize(Path(tmp))
            manager.create_session("empty")
            planner = ItineraryPlanner(
                sessions=manager,
                amap_client=FakeRouteClient(),
            )
            with self.assertRaises(ItineraryPlannerError) as ctx:
                planner.build(
                    BuildItineraryRequest(
                        session_id="empty",
                        poi_ids=["B001A0LXYZ", "B002B1MNPQ"],
                    )
                )
            self.assertEqual(ctx.exception.code, "no_feed")
            print("no_feed OK")

    def test_route_failure_falls_back_to_estimate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager, feed = _manager_with_feed(Path(tmp))
            client = MagicMock()
            client.plan_walking_route.side_effect = RuntimeError("network down")
            planner = ItineraryPlanner(sessions=manager, amap_client=client)
            response = planner.build(
                BuildItineraryRequest(
                    session_id="plan-test",
                    poi_ids=feed.poi_ids[:2],
                )
            )
            self.assertTrue(any("路径规划失败" in w for w in response.warnings))
            self.assertGreater(response.itinerary.total_distance_m, 0)
            print("route fallback OK")


class TestDwellHeuristics(unittest.TestCase):
    def test_estimate_dwell_min(self) -> None:
        from domain.poi import POIItem

        cafe = POIItem(
            id="c1",
            name="咖啡馆",
            type="餐饮服务;咖啡厅",
            location=GeoLocation(lng=1, lat=2),
        )
        museum = POIItem(
            id="m1",
            name="美术馆",
            type="科教文化服务;美术馆",
            location=GeoLocation(lng=1, lat=2),
        )
        self.assertEqual(estimate_dwell_min(cafe), 45)
        self.assertEqual(estimate_dwell_min(museum), 90)
        print("dwell heuristics OK")


if __name__ == "__main__":
    unittest.main()
