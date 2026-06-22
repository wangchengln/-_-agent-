#!/usr/bin/env python3
"""Unit tests for Amap LangChain tools (mocked client)."""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from domain.poi import POIItem
from domain.types import GeoLocation
from tools.amap_client import RoutePlan, RouteStep, WeatherCast, WeatherInfo, WeatherLive
from tools.amap_poi_tool import create_amap_poi_tool
from tools.amap_route_tool import create_amap_route_tool
from tools.amap_weather_tool import create_amap_weather_tool


def _sample_poi() -> POIItem:
    return POIItem(
        id="B000001",
        name="测试咖啡馆",
        type="餐饮服务;咖啡厅",
        address="上海市黄浦区南京东路",
        location=GeoLocation(lng=121.48, lat=31.24, city="上海"),
        rating=4.5,
        cost="40.00",
        cost_numeric=40.0,
        distance_m=350.0,
        tags=["咖啡", "安静"],
        description="测试咖啡馆",
    )


class AmapToolsUnitTests(unittest.TestCase):
    @patch("tools.amap_poi_tool.get_amap_client")
    def test_poi_tool_nearby_search(self, mock_get_client: MagicMock) -> None:
        client = mock_get_client.return_value
        client.search_around.return_value = [_sample_poi()]

        tool = create_amap_poi_tool()
        output = tool.invoke(
            {
                "keywords": "咖啡",
                "lng": 121.475,
                "lat": 31.233,
                "radius": 2000,
                "limit": 5,
            }
        )

        self.assertIn("测试咖啡馆", output)
        self.assertIn("Structured POI JSON", output)
        client.search_around.assert_called_once()

        json_part = output.split("```json\n", 1)[1].rsplit("\n```", 1)[0]
        payload = json.loads(json_part)
        self.assertEqual(payload[0]["id"], "B000001")

    @patch("tools.amap_poi_tool.get_amap_client")
    def test_poi_tool_geocode_address_then_nearby(self, mock_get_client: MagicMock) -> None:
        client = mock_get_client.return_value
        client.geocode.return_value = GeoLocation(
            lng=121.475,
            lat=31.233,
            city="上海",
            address="上海市人民广场",
        )
        client.search_around.return_value = [_sample_poi()]

        tool = create_amap_poi_tool()
        output = tool.invoke(
            {
                "keywords": "咖啡",
                "address": "上海市人民广场",
                "city": "上海",
            }
        )

        self.assertIn("Anchor address: 上海市人民广场", output)
        client.geocode.assert_called_once_with("上海市人民广场", city="上海")
        client.search_around.assert_called_once()

    @patch("tools.amap_poi_tool.get_amap_client")
    def test_poi_tool_city_search(self, mock_get_client: MagicMock) -> None:
        client = mock_get_client.return_value
        client.search_poi.return_value = [_sample_poi()]

        tool = create_amap_poi_tool()
        output = tool.invoke(
            {
                "keywords": "博物馆",
                "city": "上海",
                "search_mode": "city",
            }
        )

        self.assertIn("Amap city POI search", output)
        client.search_poi.assert_called_once()

    @patch("tools.amap_weather_tool.get_amap_client")
    def test_weather_tool(self, mock_get_client: MagicMock) -> None:
        client = mock_get_client.return_value
        client.weather.return_value = WeatherInfo(
            city="上海市",
            adcode="310000",
            lives=[
                WeatherLive(
                    city="上海市",
                    adcode="310000",
                    weather="小雨",
                    temperature="26",
                    reporttime="2026-06-20 12:00:00",
                )
            ],
            casts=[
                WeatherCast(
                    date="2026-06-20",
                    dayweather="小雨",
                    nightweather="阴",
                    daytemp="26",
                    nighttemp="22",
                )
            ],
        )

        tool = create_amap_weather_tool()
        output = tool.invoke({"city": "310000", "extensions": "all"})

        self.assertIn("Rainy heuristic: True", output)
        self.assertIn("Forecast:", output)

    @patch("tools.amap_route_tool.get_amap_client")
    def test_route_tool_walking(self, mock_get_client: MagicMock) -> None:
        client = mock_get_client.return_value
        origin = GeoLocation(lng=121.47, lat=31.23)
        destination = GeoLocation(lng=121.48, lat=31.24)
        client.plan_walking_route.return_value = RoutePlan(
            mode="walking",
            distance_m=1200,
            duration_s=900,
            origin=origin,
            destination=destination,
            steps=[
                RouteStep(
                    instruction="沿南京路向东步行",
                    distance_m=1200,
                    duration_s=900,
                )
            ],
        )

        tool = create_amap_route_tool()
        output = tool.invoke(
            {
                "origin_lng": 121.47,
                "origin_lat": 31.23,
                "dest_lng": 121.48,
                "dest_lat": 31.24,
                "mode": "walking",
            }
        )

        self.assertIn("Mode: walking", output)
        self.assertIn("Distance: 1200m", output)
        client.plan_walking_route.assert_called_once()

    @patch("tools.amap_route_tool.get_amap_client")
    def test_route_tool_geocode_addresses(self, mock_get_client: MagicMock) -> None:
        client = mock_get_client.return_value
        client.geocode.side_effect = [
            GeoLocation(lng=121.47, lat=31.23, city="上海", address="起点"),
            GeoLocation(lng=121.48, lat=31.24, city="上海", address="终点"),
        ]
        client.plan_driving_route.return_value = RoutePlan(
            mode="driving",
            distance_m=5000,
            duration_s=1200,
            origin=GeoLocation(lng=121.47, lat=31.23),
            destination=GeoLocation(lng=121.48, lat=31.24),
            steps=[],
        )

        tool = create_amap_route_tool()
        output = tool.invoke(
            {
                "origin_address": "上海市人民广场",
                "dest_address": "外滩",
                "mode": "driving",
                "city": "上海",
            }
        )

        self.assertIn("Mode: driving", output)
        self.assertEqual(client.geocode.call_count, 2)
        client.plan_driving_route.assert_called_once()

    def test_tools_registered(self) -> None:
        from pathlib import Path
        from tools import get_all_tools

        tools = get_all_tools(Path("."))
        names = {tool.name for tool in tools}
        self.assertIn("amap_search_poi", names)
        self.assertIn("amap_weather", names)
        self.assertIn("amap_route_plan", names)
        self.assertEqual(len(tools), 10)


if __name__ == "__main__":
    unittest.main()
