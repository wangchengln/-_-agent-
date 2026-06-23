"""Weather hook — fetch Amap weather and inject rainy-day hard constraints.

Runs before candidate recall in :class:`ScoringPipeline`. When rain is detected,
``positive_hard.venue_type`` is set to ``indoor`` unless the user explicitly
requested outdoor venues. Failures degrade gracefully (no injection).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from domain.preference import PreferenceProfile
from domain.types import VenueType
from domain.weather import WeatherSnapshot
from tools.amap_client import AmapClientError, AmapConfigError, WeatherInfo

logger = logging.getLogger(__name__)

RULE_INJECT_INDOOR = "检测到雨天，已自动优先推荐室内场所"
RULE_SKIPPED_OUTDOOR = "检测到雨天，但您偏好室外活动，未自动调整筛选条件"


@dataclass(frozen=True)
class WeatherAdjustment:
    """Preference possibly modified for weather, plus a wire-friendly snapshot."""

    preference: PreferenceProfile
    weather: WeatherSnapshot | None


def resolve_weather_city(preference: PreferenceProfile) -> str | None:
    """Return Amap ``city`` query (adcode preferred, then city name)."""
    anchor = preference.anchor
    if anchor is None:
        return None
    if anchor.adcode and anchor.adcode.strip():
        return anchor.adcode.strip()
    if anchor.city and anchor.city.strip():
        return anchor.city.strip()
    return None


def _weather_summary(info: WeatherInfo) -> str:
    if info.lives:
        return info.lives[0].weather or ""
    if info.casts:
        return info.casts[0].dayweather or ""
    return ""


def _weather_temperature(info: WeatherInfo) -> str | None:
    if info.lives and info.lives[0].temperature:
        return info.lives[0].temperature
    return None


def build_weather_snapshot(
    info: WeatherInfo,
    *,
    query: str,
    injected_rule: str | None = None,
) -> WeatherSnapshot:
    return WeatherSnapshot(
        city=info.city or query,
        adcode=info.adcode or "",
        summary=_weather_summary(info),
        temperature=_weather_temperature(info),
        is_rainy=info.is_rainy,
        injected_rule=injected_rule,
        fetched=True,
    )


def apply_rainy_injection(
    preference: PreferenceProfile,
    info: WeatherInfo,
) -> tuple[PreferenceProfile, str | None]:
    """Return preference with indoor hard constraint when rainy, if appropriate."""
    if not info.is_rainy:
        return preference, None

    venue = preference.positive_hard.venue_type
    if venue == VenueType.OUTDOOR:
        return preference, RULE_SKIPPED_OUTDOOR
    if venue == VenueType.INDOOR:
        return preference, None

    adjusted = preference.model_copy(deep=True)
    adjusted.positive_hard.venue_type = VenueType.INDOOR
    return adjusted, RULE_INJECT_INDOOR


def fetch_weather_info(client: Any, city: str) -> WeatherInfo | None:
    try:
        return client.weather(city)
    except (AmapClientError, AmapConfigError) as exc:
        logger.warning("weather fetch failed for %r: %s", city, exc)
        return None
    except Exception as exc:  # noqa: BLE001 — never break scoring on weather
        logger.warning("unexpected weather error for %r: %s", city, exc)
        return None


def adjust_preference_for_weather(
    preference: PreferenceProfile,
    *,
    client: Any | None = None,
) -> WeatherAdjustment:
    """Fetch weather for the anchor and optionally inject rainy-day constraints."""
    city = resolve_weather_city(preference)
    if not city:
        return WeatherAdjustment(preference=preference, weather=None)

    if client is None:
        try:
            from tools.amap_client import get_amap_client

            client = get_amap_client()
        except AmapConfigError as exc:
            logger.warning("weather hook skipped: %s", exc)
            return WeatherAdjustment(
                preference=preference,
                weather=WeatherSnapshot(city=city, fetched=False),
            )

    info = fetch_weather_info(client, city)
    if info is None:
        return WeatherAdjustment(
            preference=preference,
            weather=WeatherSnapshot(city=city, fetched=False),
        )

    adjusted, rule = apply_rainy_injection(preference, info)
    snapshot = build_weather_snapshot(info, query=city, injected_rule=rule)
    return WeatherAdjustment(preference=adjusted, weather=snapshot)
