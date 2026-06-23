"""Unified HTTP client for Amap (高德) Web Service API v3."""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from domain.poi import POIItem, parse_amap_pois
from domain.types import GeoLocation
from tools.amap_keys import get_amap_web_service_key


class AmapClientError(Exception):
    """Base error for Amap client failures."""


class AmapConfigError(AmapClientError):
    """Raised when API key is missing or invalid configuration."""


class AmapApiError(AmapClientError):
    """Raised when Amap API returns a non-success status."""

    def __init__(self, message: str, *, code: str | None = None, info: str | None = None):
        super().__init__(message)
        self.code = code
        self.info = info


class WeatherCast(BaseModel):
    """Single-day weather forecast."""

    date: str = ""
    week: str = ""
    dayweather: str = ""
    nightweather: str = ""
    daytemp: str = ""
    nighttemp: str = ""
    daywind: str = ""
    nightwind: str = ""
    daypower: str = ""
    nightpower: str = ""


class WeatherLive(BaseModel):
    """Current weather snapshot (extensions=base)."""

    province: str = ""
    city: str = ""
    adcode: str = ""
    weather: str = ""
    temperature: str = ""
    winddirection: str = ""
    windpower: str = ""
    humidity: str = ""
    reporttime: str = ""


class WeatherInfo(BaseModel):
    """Normalized weather response."""

    city: str = ""
    adcode: str = ""
    province: str = ""
    reporttime: str = ""
    lives: list[WeatherLive] = Field(default_factory=list)
    casts: list[WeatherCast] = Field(default_factory=list)

    @property
    def is_rainy(self) -> bool:
        """Heuristic: whether current or today's forecast suggests rain."""
        rainy_keywords = ("雨", "雷", "雪", "雹")
        for live in self.lives:
            if any(keyword in live.weather for keyword in rainy_keywords):
                return True
        for cast in self.casts[:1]:
            if any(keyword in cast.dayweather for keyword in rainy_keywords):
                return True
            if any(keyword in cast.nightweather for keyword in rainy_keywords):
                return True
        return False


class RouteStep(BaseModel):
    """One step in a route plan."""

    instruction: str = ""
    distance_m: int = 0
    duration_s: int = 0


class RoutePlan(BaseModel):
    """Normalized route planning result."""

    mode: Literal["walking", "driving", "transit"] = "walking"
    distance_m: int = 0
    duration_s: int = 0
    origin: GeoLocation
    destination: GeoLocation
    steps: list[RouteStep] = Field(default_factory=list)


class AmapClient:
    """Amap REST client with caching, error handling, and domain normalization."""

    DEFAULT_BASE_URL = "https://restapi.amap.com/v3"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 10.0,
        cache_ttl: int = 300,
        cache_enabled: bool = True,
    ) -> None:
        self.api_key = api_key or get_amap_web_service_key()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self.cache_enabled = cache_enabled
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def clear_cache(self) -> None:
        """Clear in-memory response cache."""
        self._cache.clear()

    def _ensure_api_key(self) -> str:
        if not self.api_key:
            raise AmapConfigError(
                "AMAP_WEB_SERVICE_KEY is not configured. "
                "Add it to backend/.env (Web 服务 Key，非 JS API Key)"
            )
        return self.api_key

    @staticmethod
    def _cache_key(path: str, params: dict[str, Any]) -> str:
        payload = json.dumps({"path": path, "params": params}, sort_keys=True)
        return hashlib.md5(payload.encode("utf-8")).hexdigest()

    def _get_cached(self, key: str) -> dict[str, Any] | None:
        if not self.cache_enabled:
            return None
        cached = self._cache.get(key)
        if not cached:
            return None
        expires_at, payload = cached
        if time.time() >= expires_at:
            self._cache.pop(key, None)
            return None
        return payload

    def _set_cache(self, key: str, payload: dict[str, Any]) -> None:
        if not self.cache_enabled:
            return
        self._cache[key] = (time.time() + self.cache_ttl, payload)

    def _request(
        self,
        path: str,
        params: dict[str, Any],
        *,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Perform GET request against Amap API with optional cache."""
        api_key = self._ensure_api_key()
        query = {key: value for key, value in params.items() if value is not None}
        query["key"] = api_key

        cache_key = self._cache_key(path, query)
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=query)
                if response.status_code >= 400:
                    raise AmapClientError(
                        f"Amap HTTP {response.status_code}: {response.text[:200]}"
                    )
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise AmapClientError(f"Amap request timed out: {url}") from exc
        except httpx.HTTPError as exc:
            raise AmapClientError(f"Amap HTTP error: {exc}") from exc
        except ValueError as exc:
            raise AmapClientError("Amap returned invalid JSON") from exc

        status = str(payload.get("status", ""))
        if status != "1":
            info = str(payload.get("info", "unknown error"))
            code = str(payload.get("infocode", ""))
            raise AmapApiError(
                f"Amap API error: {info} (code={code})",
                code=code or None,
                info=info,
            )

        if use_cache:
            self._set_cache(cache_key, payload)
        return payload

    @staticmethod
    def _first_or_error(items: list[dict[str, Any]], *, what: str) -> dict[str, Any]:
        if not items:
            raise AmapApiError(f"Amap returned no {what}")
        return items[0]

    def geocode(self, address: str, *, city: str | None = None) -> GeoLocation:
        """Convert address to coordinates (/geocode/geo)."""
        payload = self._request(
            "geocode/geo",
            {"address": address, "city": city},
        )
        geocode = self._first_or_error(payload.get("geocodes", []), what="geocode")
        location = GeoLocation.from_amap_location(
            geocode["location"],
            city=geocode.get("city") or city,
            adcode=geocode.get("adcode"),
            address=geocode.get("formatted_address") or address,
        )
        return location

    def regeocode(
        self,
        lng: float,
        lat: float,
        *,
        radius: int = 1000,
    ) -> GeoLocation:
        """Convert coordinates to address (/geocode/regeo)."""
        payload = self._request(
            "geocode/regeo",
            {
                "location": f"{lng},{lat}",
                "radius": radius,
                "extensions": "base",
            },
        )
        regeocode = payload.get("regeocode") or {}
        address = regeocode.get("formatted_address", "")
        component = regeocode.get("addressComponent") or {}
        return GeoLocation(
            lng=lng,
            lat=lat,
            city=component.get("city") or component.get("province"),
            adcode=component.get("adcode"),
            address=address,
        )

    def search_poi(
        self,
        keywords: str,
        *,
        city: str | None = None,
        types: str | None = None,
        page: int = 1,
        offset: int = 20,
        keep_raw: bool = False,
    ) -> list[POIItem]:
        """Keyword POI search (/place/text)."""
        payload = self._request(
            "place/text",
            {
                "keywords": keywords,
                "city": city,
                "types": types,
                "offset": offset,
                "page": page,
                "extensions": "all",
            },
        )
        pois = payload.get("pois") or []
        return parse_amap_pois(pois, anchor_city=city, keep_raw=keep_raw)

    def search_around(
        self,
        lng: float,
        lat: float,
        *,
        keywords: str = "",
        radius: int = 3000,
        types: str | None = None,
        sortrule: Literal["distance", "weight"] = "distance",
        page: int = 1,
        offset: int = 20,
        anchor_city: str | None = None,
        keep_raw: bool = False,
    ) -> list[POIItem]:
        """Nearby POI search (/place/around)."""
        payload = self._request(
            "place/around",
            {
                "location": f"{lng},{lat}",
                "keywords": keywords or None,
                "radius": radius,
                "types": types,
                "sortrule": sortrule,
                "offset": offset,
                "page": page,
                "extensions": "all",
            },
        )
        pois = payload.get("pois") or []
        return parse_amap_pois(pois, anchor_city=anchor_city, keep_raw=keep_raw)

    def input_tips(
        self,
        keywords: str,
        *,
        city: str | None = None,
        types: str | None = None,
    ) -> list[dict[str, Any]]:
        """Input suggestion API (/assistant/inputtips)."""
        payload = self._request(
            "assistant/inputtips",
            {
                "keywords": keywords,
                "city": city,
                "type": types,
            },
        )
        tips = payload.get("tips") or []
        return [tip for tip in tips if isinstance(tip, dict)]

    def weather(
        self,
        city: str,
        *,
        extensions: Literal["base", "all"] = "all",
    ) -> WeatherInfo:
        """Query weather by city name or adcode (/weather/weatherInfo)."""
        payload = self._request(
            "weather/weatherInfo",
            {"city": city, "extensions": extensions},
        )
        lives = [WeatherLive.model_validate(item) for item in payload.get("lives") or []]
        casts: list[WeatherCast] = []
        for forecast in payload.get("forecasts") or []:
            casts.extend(
                WeatherCast.model_validate(item)
                for item in forecast.get("casts") or []
            )
            if not lives:
                lives.append(
                    WeatherLive(
                        province=forecast.get("province", ""),
                        city=forecast.get("city", ""),
                        adcode=forecast.get("adcode", ""),
                        reporttime=forecast.get("reporttime", ""),
                    )
                )
        primary = lives[0] if lives else WeatherLive()
        return WeatherInfo(
            city=primary.city,
            adcode=primary.adcode,
            province=primary.province,
            reporttime=primary.reporttime,
            lives=lives,
            casts=casts,
        )

    def _parse_route(
        self,
        payload: dict[str, Any],
        *,
        mode: Literal["walking", "driving", "transit"],
        origin: GeoLocation,
        destination: GeoLocation,
    ) -> RoutePlan:
        route = payload.get("route") or {}
        paths = route.get("paths") or route.get("transits") or []
        if not paths:
            raise AmapApiError(f"Amap returned no {mode} route")

        best = paths[0]
        steps: list[RouteStep] = []
        for step in best.get("steps") or []:
            steps.append(
                RouteStep(
                    instruction=str(step.get("instruction", "")),
                    distance_m=int(float(step.get("distance", 0) or 0)),
                    duration_s=int(float(step.get("duration", 0) or 0)),
                )
            )

        return RoutePlan(
            mode=mode,
            distance_m=int(float(best.get("distance", 0) or 0)),
            duration_s=int(float(best.get("duration", 0) or 0)),
            origin=origin,
            destination=destination,
            steps=steps,
        )

    def plan_walking_route(
        self,
        origin: GeoLocation,
        destination: GeoLocation,
    ) -> RoutePlan:
        """Walking route plan (/direction/walking)."""
        payload = self._request(
            "direction/walking",
            {
                "origin": origin.to_amap_location(),
                "destination": destination.to_amap_location(),
            },
            use_cache=False,
        )
        return self._parse_route(
            payload,
            mode="walking",
            origin=origin,
            destination=destination,
        )

    def plan_driving_route(
        self,
        origin: GeoLocation,
        destination: GeoLocation,
        *,
        strategy: int = 0,
    ) -> RoutePlan:
        """Driving route plan (/direction/driving)."""
        payload = self._request(
            "direction/driving",
            {
                "origin": origin.to_amap_location(),
                "destination": destination.to_amap_location(),
                "strategy": strategy,
            },
            use_cache=False,
        )
        return self._parse_route(
            payload,
            mode="driving",
            origin=origin,
            destination=destination,
        )

    def plan_transit_route(
        self,
        origin: GeoLocation,
        destination: GeoLocation,
        *,
        city: str,
        strategy: int = 0,
    ) -> RoutePlan:
        """Public transit route plan (/direction/transit/integrated)."""
        payload = self._request(
            "direction/transit/integrated",
            {
                "origin": origin.to_amap_location(),
                "destination": destination.to_amap_location(),
                "city": city,
                "strategy": strategy,
            },
            use_cache=False,
        )
        return self._parse_route(
            payload,
            mode="transit",
            origin=origin,
            destination=destination,
        )

    def distance_matrix(
        self,
        origins: list[GeoLocation],
        destinations: list[GeoLocation],
        *,
        mode: Literal["0", "1", "3"] = "1",
    ) -> list[dict[str, Any]]:
        """Batch distance/duration measurement (/distance).

        mode: 0=直线, 1=驾车, 3=步行
        """
        if not origins or not destinations:
            return []
        origin_str = "|".join(item.to_amap_location() for item in origins)
        dest_str = "|".join(item.to_amap_location() for item in destinations)
        payload = self._request(
            "distance",
            {
                "origins": origin_str,
                "destination": dest_str,
                "type": mode,
            },
            use_cache=False,
        )
        results = payload.get("results") or []
        return [item for item in results if isinstance(item, dict)]


_default_client: AmapClient | None = None


def get_amap_client() -> AmapClient:
    """Return process-wide default Amap client."""
    global _default_client
    if _default_client is None:
        _default_client = AmapClient()
    return _default_client
