"""Itinerary planner — order stops, allocate time, plan routes (Day 6.4).

Deterministic orchestration (no LLM):
  resolve POIs from session feed -> nearest-neighbor ordering -> dwell times
  -> Amap route legs -> :class:`WeekendItinerary`
"""

from __future__ import annotations

import logging
import math
from typing import Any

from domain.feed import RecommendationFeed
from domain.itinerary import (
    BuildItineraryRequest,
    BuildItineraryResponse,
    ItineraryLeg,
    ItineraryStop,
    TransportMode,
    WeekendItinerary,
    format_time_minutes,
    parse_time_minutes,
)
from domain.poi import POIItem
from domain.types import GeoLocation
from graph.session_manager import SessionManager, session_manager
from recsys.itinerary_errors import ItineraryPlannerError
from tools.amap_client import AmapClientError, AmapConfigError, RoutePlan

logger = logging.getLogger(__name__)

_WALKING_SPEED_MPS = 1.2
_DRIVING_SPEED_MPS = 8.3  # ~30 km/h urban average

_FOOD_MARKERS = ("餐", "饭", "美食", "小吃", "料理")
_CAFE_MARKERS = ("咖啡", "咖啡厅", "茶饮", "奶茶")
_CULTURE_MARKERS = ("展览", "美术馆", "博物馆", "科教文化", "图书馆")
_SCENIC_MARKERS = ("风景", "公园", "绿道", "名胜", "历史建筑")


class ItineraryPlanner:
    """Build a weekend itinerary from feed POIs selected by the user."""

    def __init__(
        self,
        *,
        sessions: SessionManager | None = None,
        amap_client: Any | None = None,
    ) -> None:
        self._sessions = sessions or session_manager
        self._amap_client = amap_client

    def build(self, request: BuildItineraryRequest) -> BuildItineraryResponse:
        """Plan an itinerary and persist it on the session IRF state."""
        state = self._sessions.get_irf_state(request.session_id)
        feed = state.current_feed
        if feed is None or not feed.items:
            raise ItineraryPlannerError("no_feed")

        pois = _resolve_pois(feed, request.poi_ids)
        _ensure_poi_coordinates(pois)

        route_origin = _resolve_route_origin(state.preference.anchor, feed)
        sort_origin = route_origin if _has_coordinates(route_origin) else pois[0].location

        if request.anchor_poi_id and request.anchor_poi_id not in {p.id for p in pois}:
            raise ItineraryPlannerError("invalid_anchor_poi")

        ordered = _order_pois(
            pois,
            sort_origin,
            anchor_poi_id=request.anchor_poi_id,
        )

        client = self._get_client()
        warnings: list[str] = []
        if not _has_coordinates(route_origin):
            warnings.append("锚点无坐标，已从第一个站点开始规划（未计入前往首站的通勤）。")
            travel_origin: GeoLocation | None = None
        else:
            travel_origin = route_origin

        day_end_min = parse_time_minutes(request.day_end)
        cursor = parse_time_minutes(request.day_start)

        stops: list[ItineraryStop] = []
        legs: list[ItineraryLeg] = []
        total_distance_m = 0
        total_travel_min = 0
        total_dwell_min = 0

        transit_city = _transit_city(route_origin, feed)

        for index, poi in enumerate(ordered):
            if index == 0 and travel_origin is not None:
                leg = _plan_leg(
                    client,
                    travel_origin,
                    poi.location,
                    mode=request.transport_mode,
                    city=transit_city,
                )
                if leg.estimated:
                    warnings.append(
                        f"前往「{poi.name}」的路径规划失败，已用直线距离估算。"
                    )
                travel_min = max(1, math.ceil(leg.duration_s / 60)) if leg.distance_m else 0
                cursor = cursor + travel_min
                total_distance_m += leg.distance_m
                total_travel_min += travel_min
            elif index > 0:
                prev = ordered[index - 1]
                leg = _plan_leg(
                    client,
                    prev.location,
                    poi.location,
                    mode=request.transport_mode,
                    city=transit_city,
                )
                if leg.estimated:
                    warnings.append(
                        f"「{prev.name}」→「{poi.name}」路径规划失败，已用直线距离估算。"
                    )
                travel_min = max(1, math.ceil(leg.duration_s / 60)) if leg.distance_m else 0
                depart_min = cursor
                arrive_min = cursor + travel_min
                legs.append(
                    ItineraryLeg(
                        from_poi_id=prev.id,
                        to_poi_id=poi.id,
                        mode=request.transport_mode,
                        distance_m=leg.distance_m,
                        duration_s=leg.duration_s,
                        depart_at=format_time_minutes(depart_min),
                        arrive_at=format_time_minutes(arrive_min),
                        path=leg.path,
                        estimated=leg.estimated,
                    )
                )
                total_distance_m += leg.distance_m
                total_travel_min += travel_min
                cursor = arrive_min

            dwell_min = estimate_dwell_min(poi)
            leave_min = cursor + dwell_min
            stops.append(
                ItineraryStop(
                    order=index + 1,
                    poi_id=poi.id,
                    name=poi.name,
                    type=poi.type,
                    lng=poi.location.lng,
                    lat=poi.location.lat,
                    address=poi.address,
                    arrive_at=format_time_minutes(cursor),
                    leave_at=format_time_minutes(leave_min),
                    dwell_min=dwell_min,
                )
            )
            total_dwell_min += dwell_min
            cursor = leave_min

        if cursor > day_end_min:
            warnings.append("时间偏紧，建议减少站点或缩短停留时间。")

        itinerary_legs = legs

        display_anchor = (
            route_origin
            if _has_coordinates(route_origin)
            else ordered[0].location
        )

        itinerary = WeekendItinerary(
            session_id=request.session_id,
            round=feed.round,
            anchor=display_anchor,
            transport_mode=request.transport_mode,
            day_start=request.day_start,
            day_end=request.day_end,
            stops=stops,
            legs=itinerary_legs,
            total_distance_m=total_distance_m,
            total_travel_min=total_travel_min,
            total_dwell_min=total_dwell_min,
            weather=feed.weather,
            warnings=list(dict.fromkeys(warnings)),
        )

        self._sessions.save_irf_state(
            request.session_id,
            state.with_itinerary(itinerary),
        )

        return BuildItineraryResponse(
            itinerary=itinerary,
            warnings=itinerary.warnings,
        )

    def _get_client(self) -> Any | None:
        if self._amap_client is not None:
            return self._amap_client
        try:
            from tools.amap_client import get_amap_client

            return get_amap_client()
        except AmapConfigError as exc:
            logger.warning("itinerary planner: Amap client unavailable: %s", exc)
            return None


def _resolve_pois(feed: RecommendationFeed, poi_ids: list[str]) -> list[POIItem]:
    by_id = {scored.item.id: scored.item for scored in feed.items}
    missing = [poi_id for poi_id in poi_ids if poi_id not in by_id]
    if missing:
        raise ItineraryPlannerError(
            "poi_not_found",
            detail="、".join(missing),
        )
    return [by_id[poi_id] for poi_id in poi_ids]


def _resolve_route_origin(
    session_anchor: GeoLocation | None,
    feed: RecommendationFeed,
) -> GeoLocation:
    if session_anchor and _has_coordinates(session_anchor):
        return session_anchor

    feed_anchor = feed.preference_snapshot.anchor
    if feed_anchor and _has_coordinates(feed_anchor):
        return feed_anchor

    if session_anchor:
        return session_anchor
    if feed_anchor:
        return feed_anchor

    return GeoLocation()


def _order_pois(
    pois: list[POIItem],
    anchor: GeoLocation,
    *,
    anchor_poi_id: str | None,
) -> list[POIItem]:
    if len(pois) == 1:
        return list(pois)

    if anchor_poi_id:
        first = next(poi for poi in pois if poi.id == anchor_poi_id)
        rest = [poi for poi in pois if poi.id != anchor_poi_id]
        return [first] + _nearest_neighbor(rest, first.location)

    start = anchor if _has_coordinates(anchor) else pois[0].location
    return _nearest_neighbor(pois, start)


def _nearest_neighbor(pois: list[POIItem], start: GeoLocation) -> list[POIItem]:
    remaining = list(pois)
    ordered: list[POIItem] = []
    current = start
    while remaining:
        next_poi = min(
            remaining,
            key=lambda poi: _distance_m(current, poi.location) or float("inf"),
        )
        ordered.append(next_poi)
        remaining.remove(next_poi)
        current = next_poi.location
    return ordered


def _has_coordinates(location: GeoLocation) -> bool:
    return location.lng is not None and location.lat is not None


def _ensure_poi_coordinates(pois: list[POIItem]) -> None:
    missing = [poi.id for poi in pois if not _has_coordinates(poi.location)]
    if missing:
        raise ItineraryPlannerError(
            "missing_coords",
            detail="、".join(missing),
        )


def estimate_dwell_min(poi: POIItem) -> int:
    """Heuristic stay duration from POI type/tags."""
    blob = f"{poi.type} {' '.join(poi.tags)}"
    if any(marker in blob for marker in _CAFE_MARKERS):
        return 45
    if any(marker in blob for marker in _FOOD_MARKERS):
        return 60
    if any(marker in blob for marker in _CULTURE_MARKERS):
        return 90
    if any(marker in blob for marker in _SCENIC_MARKERS):
        return 90
    return 60


def _transit_city(anchor: GeoLocation, feed: RecommendationFeed) -> str:
    if anchor.city:
        return anchor.city
    feed_anchor = feed.preference_snapshot.anchor
    if feed_anchor and feed_anchor.city:
        return feed_anchor.city
    if anchor.adcode:
        return anchor.adcode
    return "上海"


class _LegPlan:
    __slots__ = ("distance_m", "duration_s", "path", "estimated")

    def __init__(
        self,
        *,
        distance_m: int,
        duration_s: int,
        path: list[list[float]],
        estimated: bool,
    ) -> None:
        self.distance_m = distance_m
        self.duration_s = duration_s
        self.path = path
        self.estimated = estimated


def _plan_leg(
    client: Any | None,
    origin: GeoLocation,
    destination: GeoLocation,
    *,
    mode: TransportMode,
    city: str,
) -> _LegPlan:
    if client is not None:
        try:
            route = _fetch_route(client, origin, destination, mode=mode, city=city)
            path = _straight_path(origin, destination)
            return _LegPlan(
                distance_m=route.distance_m,
                duration_s=route.duration_s,
                path=path,
                estimated=False,
            )
        except Exception as exc:  # noqa: BLE001 — degrade to straight-line estimate
            logger.warning("route plan failed %s -> %s: %s", origin, destination, exc)

    return _estimate_leg(origin, destination, mode=mode)


def _fetch_route(
    client: Any,
    origin: GeoLocation,
    destination: GeoLocation,
    *,
    mode: TransportMode,
    city: str,
) -> RoutePlan:
    if mode == "walking":
        return client.plan_walking_route(origin, destination)
    if mode == "driving":
        return client.plan_driving_route(origin, destination)
    return client.plan_transit_route(origin, destination, city=city)


def _estimate_leg(
    origin: GeoLocation,
    destination: GeoLocation,
    *,
    mode: TransportMode,
) -> _LegPlan:
    distance_m = int(_distance_m(origin, destination) or 0)
    speed = _DRIVING_SPEED_MPS if mode == "driving" else _WALKING_SPEED_MPS
    duration_s = int(distance_m / speed) if distance_m > 0 else 0
    return _LegPlan(
        distance_m=distance_m,
        duration_s=duration_s,
        path=_straight_path(origin, destination),
        estimated=True,
    )


def _straight_path(origin: GeoLocation, destination: GeoLocation) -> list[list[float]]:
    if not _has_coordinates(origin) or not _has_coordinates(destination):
        return []
    assert origin.lng is not None and origin.lat is not None
    assert destination.lng is not None and destination.lat is not None
    return [
        [origin.lng, origin.lat],
        [destination.lng, destination.lat],
    ]


def _distance_m(a: GeoLocation, b: GeoLocation) -> float | None:
    if not _has_coordinates(a) or not _has_coordinates(b):
        return None
    assert a.lng is not None and a.lat is not None
    assert b.lng is not None and b.lat is not None
    return _haversine_m(a.lng, a.lat, b.lng, b.lat)


def _haversine_m(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    sin_half = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * radius * math.asin(min(1.0, math.sqrt(sin_half)))


itinerary_planner = ItineraryPlanner()
