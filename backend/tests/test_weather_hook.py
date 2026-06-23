#!/usr/bin/env python3
"""Unit tests for weather hook (Day 6.2)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from domain.preference import PreferenceProfile
from domain.types import GeoLocation, VenueType
from recsys.filter import apply_filter
from recsys.weather_hook import (
    RULE_INJECT_INDOOR,
    RULE_SKIPPED_OUTDOOR,
    adjust_preference_for_weather,
    apply_rainy_injection,
    resolve_weather_city,
)
from tools.amap_client import AmapConfigError, WeatherCast, WeatherInfo, WeatherLive


def _pref(*, venue_type: VenueType = VenueType.ANY) -> PreferenceProfile:
    pref = PreferenceProfile.empty(
        anchor=GeoLocation(lng=121.47, lat=31.23, city="上海", adcode="310100")
    )
    pref.positive_hard.venue_type = venue_type
    return pref


def _rainy_info() -> WeatherInfo:
    return WeatherInfo(
        city="上海",
        adcode="310100",
        lives=[WeatherLive(city="上海", weather="小雨", temperature="18")],
        casts=[WeatherCast(dayweather="小雨", nightweather="阴")],
    )


def _sunny_info() -> WeatherInfo:
    return WeatherInfo(
        city="上海",
        adcode="310100",
        lives=[WeatherLive(city="上海", weather="晴", temperature="26")],
        casts=[WeatherCast(dayweather="晴", nightweather="晴")],
    )


class TestResolveWeatherCity(unittest.TestCase):
    def test_prefers_adcode(self) -> None:
        self.assertEqual(resolve_weather_city(_pref()), "310100")

    def test_falls_back_to_city(self) -> None:
        pref = PreferenceProfile.empty(
            anchor=GeoLocation(lng=121.0, lat=31.0, city="杭州")
        )
        self.assertEqual(resolve_weather_city(pref), "杭州")

    def test_no_anchor(self) -> None:
        self.assertIsNone(resolve_weather_city(PreferenceProfile.empty()))


class TestApplyRainyInjection(unittest.TestCase):
    def test_injects_indoor_when_any(self) -> None:
        adjusted, rule = apply_rainy_injection(_pref(), _rainy_info())
        self.assertEqual(adjusted.positive_hard.venue_type, VenueType.INDOOR)
        self.assertEqual(rule, RULE_INJECT_INDOOR)

    def test_skips_when_outdoor_explicit(self) -> None:
        adjusted, rule = apply_rainy_injection(
            _pref(venue_type=VenueType.OUTDOOR),
            _rainy_info(),
        )
        self.assertEqual(adjusted.positive_hard.venue_type, VenueType.OUTDOOR)
        self.assertEqual(rule, RULE_SKIPPED_OUTDOOR)

    def test_no_change_when_sunny(self) -> None:
        adjusted, rule = apply_rainy_injection(_pref(), _sunny_info())
        self.assertEqual(adjusted.positive_hard.venue_type, VenueType.ANY)
        self.assertIsNone(rule)


class TestAdjustPreferenceForWeather(unittest.TestCase):
    def test_rainy_injects_indoor_via_client(self) -> None:
        client = MagicMock()
        client.weather.return_value = _rainy_info()
        result = adjust_preference_for_weather(_pref(), client=client)
        client.weather.assert_called_once_with("310100")
        self.assertEqual(result.preference.positive_hard.venue_type, VenueType.INDOOR)
        assert result.weather is not None
        self.assertTrue(result.weather.is_rainy)
        self.assertEqual(result.weather.injected_rule, RULE_INJECT_INDOOR)
        self.assertEqual(result.weather.summary, "小雨")

    def test_sunny_no_injection(self) -> None:
        client = MagicMock()
        client.weather.return_value = _sunny_info()
        result = adjust_preference_for_weather(_pref(), client=client)
        self.assertEqual(result.preference.positive_hard.venue_type, VenueType.ANY)
        assert result.weather is not None
        self.assertFalse(result.weather.is_rainy)
        self.assertIsNone(result.weather.injected_rule)

    def test_missing_api_key_degrades(self) -> None:
        client = MagicMock()
        client.weather.side_effect = AmapConfigError("missing key")
        result = adjust_preference_for_weather(_pref(), client=client)
        self.assertEqual(result.preference.positive_hard.venue_type, VenueType.ANY)
        assert result.weather is not None
        self.assertFalse(result.weather.fetched)

    def test_no_anchor_skips_fetch(self) -> None:
        client = MagicMock()
        result = adjust_preference_for_weather(PreferenceProfile.empty(), client=client)
        client.weather.assert_not_called()
        self.assertIsNone(result.weather)


class TestWeatherFilterIntegration(unittest.TestCase):
    def test_rainy_indoor_filter_drops_outdoor_poi(self) -> None:
        from domain.poi import POIItem

        outdoor = POIItem(
            id="out",
            name="滨江绿道",
            type="风景名胜",
            location=GeoLocation(lng=121.0, lat=31.0, city="上海"),
            tags=["室外", "户外"],
            description="室外 户外 公园",
        )
        indoor = POIItem(
            id="in",
            name="美术馆",
            type="科教文化服务;美术馆",
            location=GeoLocation(lng=121.0, lat=31.0, city="上海"),
            tags=["室内"],
            description="室内 展览",
        )
        adjusted, _ = apply_rainy_injection(_pref(), _rainy_info())
        result = apply_filter([outdoor, indoor], adjusted)
        passed_ids = {poi.id for poi in result.passed}
        self.assertIn("in", passed_ids)
        self.assertNotIn("out", passed_ids)


if __name__ == "__main__":
    unittest.main()
