#!/usr/bin/env python3
"""Unit tests for AmapClient (mocked HTTP, no live API key required)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import httpx

from domain.types import GeoLocation
from tools.amap_client import (
    AmapApiError,
    AmapClient,
    AmapConfigError,
    WeatherInfo,
)


class AmapClientUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = AmapClient(api_key="test-key", cache_enabled=True, cache_ttl=60)

    def test_missing_api_key_raises(self) -> None:
        client = AmapClient(api_key=None)
        with self.assertRaises(AmapConfigError):
            client.geocode("上海市人民广场")

    @patch("tools.amap_client.httpx.Client")
    def test_geocode_parses_location(self, mock_client_cls: MagicMock) -> None:
        mock_response = httpx.Response(
            200,
            json={
                "status": "1",
                "geocodes": [
                    {
                        "formatted_address": "上海市黄浦区人民广场",
                        "location": "121.475,31.233",
                        "adcode": "310101",
                        "city": "上海市",
                    }
                ],
            },
        )
        mock_client_cls.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        location = self.client.geocode("人民广场", city="上海")
        self.assertAlmostEqual(location.lng, 121.475)
        self.assertAlmostEqual(location.lat, 31.233)
        self.assertEqual(location.adcode, "310101")
        self.assertEqual(location.city, "上海市")

    @patch("tools.amap_client.httpx.Client")
    def test_search_around_normalizes_poi(self, mock_client_cls: MagicMock) -> None:
        mock_response = httpx.Response(
            200,
            json={
                "status": "1",
                "pois": [
                    {
                        "id": "B000001",
                        "name": "测试咖啡馆",
                        "type": "餐饮服务;咖啡厅",
                        "typecode": "050500",
                        "address": "上海市黄浦区南京东路",
                        "location": "121.48,31.24",
                        "distance": "350",
                        "tag": "咖啡;安静",
                        "biz_ext": {"rating": "4.5", "cost": "40.00"},
                    }
                ],
            },
        )
        mock_client_cls.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        items = self.client.search_around(
            121.475,
            31.233,
            keywords="咖啡",
            radius=2000,
            anchor_city="上海",
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "测试咖啡馆")
        self.assertEqual(items[0].cost_numeric, 40.0)
        self.assertEqual(items[0].distance_m, 350.0)
        self.assertIn("安静", items[0].tags)

    @patch("tools.amap_client.httpx.Client")
    def test_api_error_status_raises(self, mock_client_cls: MagicMock) -> None:
        mock_response = httpx.Response(
            200,
            json={"status": "0", "info": "INVALID_USER_KEY", "infocode": "10001"},
        )
        mock_client_cls.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        with self.assertRaises(AmapApiError) as ctx:
            self.client.weather("310101")
        self.assertIn("INVALID_USER_KEY", str(ctx.exception))

    @patch("tools.amap_client.httpx.Client")
    def test_cache_avoids_second_request(self, mock_client_cls: MagicMock) -> None:
        mock_get = mock_client_cls.return_value.__enter__.return_value.get
        mock_get.return_value = httpx.Response(
            200,
            json={
                "status": "1",
                "lives": [
                    {
                        "province": "上海",
                        "city": "徐汇区",
                        "adcode": "310104",
                        "weather": "晴",
                        "temperature": "26",
                        "reporttime": "2026-06-19 12:00:00",
                    }
                ],
            },
        )

        first = self.client.weather("310104", extensions="base")
        second = self.client.weather("310104", extensions="base")
        self.assertEqual(first.city, second.city)
        self.assertEqual(mock_get.call_count, 1)

        self.client.clear_cache()
        third = self.client.weather("310104", extensions="base")
        self.assertEqual(third.city, "徐汇区")
        self.assertEqual(mock_get.call_count, 2)

    @patch("tools.amap_client.httpx.Client")
    def test_weather_is_rainy_heuristic(self, mock_client_cls: MagicMock) -> None:
        mock_client_cls.return_value.__enter__.return_value.get.return_value = (
            httpx.Response(
                200,
                json={
                    "status": "1",
                    "forecasts": [
                        {
                            "city": "上海市",
                            "adcode": "310000",
                            "province": "上海",
                            "reporttime": "2026-06-19 12:00:00",
                            "casts": [
                                {
                                    "date": "2026-06-19",
                                    "dayweather": "小雨",
                                    "nightweather": "阴",
                                    "daytemp": "24",
                                    "nighttemp": "20",
                                }
                            ],
                        }
                    ],
                },
            )
        )

        info = self.client.weather("310000")
        self.assertIsInstance(info, WeatherInfo)
        self.assertTrue(info.is_rainy)

    @patch("tools.amap_client.httpx.Client")
    def test_plan_walking_route(self, mock_client_cls: MagicMock) -> None:
        mock_client_cls.return_value.__enter__.return_value.get.return_value = (
            httpx.Response(
                200,
                json={
                    "status": "1",
                    "route": {
                        "paths": [
                            {
                                "distance": "1200",
                                "duration": "900",
                                "steps": [
                                    {
                                        "instruction": "沿XX路向东步行",
                                        "distance": "1200",
                                        "duration": "900",
                                    }
                                ],
                            }
                        ]
                    },
                },
            )
        )

        origin = GeoLocation(lng=121.47, lat=31.23)
        destination = GeoLocation(lng=121.48, lat=31.24)
        route = self.client.plan_walking_route(origin, destination)
        self.assertEqual(route.mode, "walking")
        self.assertEqual(route.distance_m, 1200)
        self.assertEqual(route.duration_s, 900)
        self.assertEqual(len(route.steps), 1)


if __name__ == "__main__":
    unittest.main()
