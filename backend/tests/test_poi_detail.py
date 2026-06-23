"""Unit tests for POI detail service and review parsing."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from domain.feed import RecommendationFeed
from domain.irf_state import IRFSessionState
from domain.poi import POIItem
from domain.poi_detail import PoiReview
from domain.types import GeoLocation
from graph.session_manager import SessionManager
from recsys.poi_detail_service import PoiDetailService
from tools.amap_reviews import fetch_poi_reviews, _normalize_review


class PoiReviewParserTests(unittest.TestCase):
    def test_normalize_review_extracts_content(self) -> None:
        review = _normalize_review(
            {
                "review": "环境很好，适合周末来坐坐",
                "user_name": "小王",
                "star": 5,
                "time": "2025-12-01",
                "pics": [{"url": "https://example.com/a.jpg"}],
            },
            0,
        )
        assert review is not None
        self.assertEqual(review.author, "小王")
        self.assertEqual(review.content, "环境很好，适合周末来坐坐")
        self.assertEqual(review.rating, 5.0)
        self.assertEqual(review.photos, ["https://example.com/a.jpg"])


class PoiDetailServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = SessionManager()
        self.manager.initialize(self._tmp_dir())

    @staticmethod
    def _tmp_dir():
        import tempfile
        from pathlib import Path

        return Path(tempfile.mkdtemp())

    def _seed_session(self, session_id: str, poi_id: str) -> None:
        loc = GeoLocation(lng=121.47, lat=31.23, city="上海", adcode="310000", address="")
        poi = POIItem(
            id=poi_id,
            name="测试咖啡馆",
            type="咖啡厅",
            address="测试路1号",
            location=loc,
            rating=4.6,
            distance_m=500.0,
            tel="021-12345678",
            tags=["咖啡", "安静"],
            photos=["https://example.com/cover.jpg"],
        )
        feed = RecommendationFeed.from_poi_items([poi], round=1, k=1)
        state = IRFSessionState.empty().with_feed(feed)
        self.manager.create_session(session_id)
        self.manager.save_irf_state(session_id, state)

    @patch("recsys.poi_detail_service.fetch_poi_reviews")
    @patch.object(PoiDetailService, "__init__", lambda self, sessions=None, amap=None: None)
    def test_get_detail_merges_feed_and_live(self, mock_reviews: MagicMock) -> None:
        session_id = "detail-test"
        poi_id = "B000TEST01"
        self._seed_session(session_id, poi_id)

        mock_reviews.return_value = (
            [
                PoiReview(
                    author="小李",
                    content="拿铁不错",
                    rating=4.5,
                    source="amap",
                )
            ],
            1,
            True,
        )

        live_loc = GeoLocation(lng=121.48, lat=31.24, city="上海", adcode="310000", address="")
        live_poi = POIItem(
            id=poi_id,
            name="测试咖啡馆(总店)",
            type="咖啡厅;精品咖啡",
            address="测试路1号101室",
            location=live_loc,
            rating=4.7,
            tel="021-87654321",
            tags=["咖啡", "安静", "可停车"],
            photos=["https://example.com/live.jpg"],
            raw={"biz_ext": {"open_time": "09:00-22:00"}},
        )

        mock_amap = MagicMock()
        mock_amap.get_poi_detail.return_value = live_poi

        service = PoiDetailService.__new__(PoiDetailService)
        service._sessions = self.manager
        service._amap = mock_amap

        detail = service.get_detail(session_id, poi_id)
        self.assertEqual(detail.name, "测试咖啡馆(总店)")
        self.assertEqual(detail.tel, "021-87654321")
        self.assertEqual(detail.open_time, "09:00-22:00")
        self.assertEqual(detail.distance_m, 500.0)
        self.assertEqual(len(detail.reviews), 1)
        self.assertTrue(detail.reviews_fetched)
        self.assertEqual(detail.reviews[0].content, "拿铁不错")


class PoiDetailApiTests(unittest.TestCase):
    @patch("tools.amap_reviews.fetch_poi_reviews", return_value=([], None, False))
    @patch("tools.amap_client.AmapClient.get_poi_detail")
    def test_api_returns_detail(self, mock_detail, _mock_reviews) -> None:
        from pathlib import Path
        import tempfile

        from fastapi.testclient import TestClient
        from app import app
        from graph.session_manager import session_manager

        session_manager.initialize(Path(tempfile.mkdtemp()))
        loc = GeoLocation(lng=121.47, lat=31.23, city="上海", adcode="310000", address="")
        poi = POIItem(
            id="B000API01",
            name="API测试店",
            type="餐厅",
            address="API路",
            location=loc,
            rating=4.2,
        )
        feed = RecommendationFeed.from_poi_items([poi], round=1, k=1)
        session_manager.create_session("api-poi-test")
        session_manager.save_irf_state(
            "api-poi-test",
            IRFSessionState.empty().with_feed(feed),
        )
        mock_detail.return_value = poi

        client = TestClient(app)
        response = client.get("/api/poi/B000API01?session_id=api-poi-test")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["poi_id"], "B000API01")
        self.assertEqual(body["name"], "API测试店")


if __name__ == "__main__":
    unittest.main()
