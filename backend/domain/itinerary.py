"""Weekend itinerary domain models (Day 6.3).

Structured output for multi-stop POI scheduling: ordered stops, inter-stop
legs (commute), optional weather snapshot, and planner warnings.
"""

from __future__ import annotations

import re
import time
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from domain.types import GeoLocation
from domain.weather import WeatherSnapshot

TransportMode = Literal["walking", "driving", "transit"]

_TIME_PATTERN = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")

MIN_ITINERARY_STOPS = 2
MAX_ITINERARY_STOPS = 5
DEFAULT_DAY_START = "09:30"
DEFAULT_DAY_END = "21:00"


def _parse_time_minutes(value: str) -> int:
    """Parse ``HH:MM`` into minutes from midnight."""
    match = _TIME_PATTERN.match(value.strip())
    if not match:
        raise ValueError(f"invalid time {value!r}, expected HH:MM")
    hours, minutes = int(match.group(1)), int(match.group(2))
    return hours * 60 + minutes


def _format_time_minutes(total_minutes: int) -> str:
    """Format minutes from midnight as ``HH:MM``."""
    total_minutes = max(0, min(total_minutes, 23 * 60 + 59))
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


parse_time_minutes = _parse_time_minutes
format_time_minutes = _format_time_minutes


class ItineraryStop(BaseModel):
    """One POI visit block on the weekend timeline."""

    order: int = Field(ge=1, description="1-based visit order")
    poi_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    type: str = Field(default="", description="Amap POI type string")
    lng: float | None = Field(default=None, description="GCJ-02 longitude")
    lat: float | None = Field(default=None, description="GCJ-02 latitude")
    address: str = Field(default="")
    arrive_at: str = Field(description="Planned arrival time HH:MM")
    leave_at: str = Field(description="Planned departure time HH:MM")
    dwell_min: int = Field(ge=0, description="Planned stay duration in minutes")

    @field_validator("poi_id", "name")
    @classmethod
    def strip_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field cannot be empty")
        return stripped

    @field_validator("arrive_at", "leave_at")
    @classmethod
    def validate_time_format(cls, value: str) -> str:
        _parse_time_minutes(value)
        return value.strip()

    @model_validator(mode="after")
    def validate_dwell_window(self) -> Self:
        arrive = _parse_time_minutes(self.arrive_at)
        leave = _parse_time_minutes(self.leave_at)
        if leave < arrive:
            raise ValueError("leave_at must not be before arrive_at")
        expected_dwell = leave - arrive
        if self.dwell_min != expected_dwell:
            raise ValueError(
                f"dwell_min ({self.dwell_min}) must match arrive/leave span ({expected_dwell})"
            )
        return self

    @property
    def has_coordinates(self) -> bool:
        return self.lng is not None and self.lat is not None


class ItineraryLeg(BaseModel):
    """Commute segment between two consecutive stops."""

    from_poi_id: str = Field(min_length=1)
    to_poi_id: str = Field(min_length=1)
    mode: TransportMode = "walking"
    distance_m: int = Field(default=0, ge=0)
    duration_s: int = Field(default=0, ge=0)
    depart_at: str = Field(description="Departure time HH:MM")
    arrive_at: str = Field(description="Arrival time HH:MM")
    path: list[list[float]] = Field(
        default_factory=list,
        description="Optional polyline as [[lng, lat], ...] for map rendering",
    )
    estimated: bool = Field(
        default=False,
        description="True when route API failed and values were estimated",
    )

    @field_validator("depart_at", "arrive_at")
    @classmethod
    def validate_time_format(cls, value: str) -> str:
        _parse_time_minutes(value)
        return value.strip()

    @field_validator("path")
    @classmethod
    def validate_path_points(cls, value: list[list[float]]) -> list[list[float]]:
        for point in value:
            if len(point) != 2:
                raise ValueError("each path point must be [lng, lat]")
        return value

    @property
    def duration_min(self) -> int:
        return max(0, self.duration_s // 60)


class WeekendItinerary(BaseModel):
    """Full weekend day plan built from selected feed POIs."""

    session_id: str = Field(default="", description="IRF session that produced this plan")
    round: int | None = Field(
        default=None,
        ge=1,
        description="IRF round when POIs were selected (if known)",
    )
    anchor: GeoLocation | None = Field(
        default=None,
        description="Trip start anchor (home / hotel / first area)",
    )
    transport_mode: TransportMode = "walking"
    day_start: str = Field(default=DEFAULT_DAY_START)
    day_end: str = Field(default=DEFAULT_DAY_END)
    stops: list[ItineraryStop] = Field(default_factory=list)
    legs: list[ItineraryLeg] = Field(default_factory=list)
    total_distance_m: int = Field(default=0, ge=0)
    total_travel_min: int = Field(default=0, ge=0)
    total_dwell_min: int = Field(default=0, ge=0)
    weather: WeatherSnapshot | None = None
    warnings: list[str] = Field(default_factory=list)
    generated_at: float = Field(default_factory=time.time)

    @field_validator("day_start", "day_end")
    @classmethod
    def validate_day_bounds(cls, value: str) -> str:
        _parse_time_minutes(value)
        return value.strip()

    @model_validator(mode="after")
    def validate_stop_order_and_legs(self) -> Self:
        if not self.stops:
            return self

        orders = [stop.order for stop in self.stops]
        expected = list(range(1, len(self.stops) + 1))
        if sorted(orders) != expected:
            raise ValueError("stop order must be contiguous starting from 1")

        if self.legs and len(self.legs) != len(self.stops) - 1:
            raise ValueError("legs count must be stops count minus 1")

        for index, leg in enumerate(self.legs):
            origin = self.stops[index]
            destination = self.stops[index + 1]
            if leg.from_poi_id != origin.poi_id or leg.to_poi_id != destination.poi_id:
                raise ValueError(
                    f"leg {index + 1} must connect stop {origin.order} to {destination.order}"
                )

        window_start = _parse_time_minutes(self.day_start)
        window_end = _parse_time_minutes(self.day_end)
        if window_end <= window_start:
            raise ValueError("day_end must be after day_start")

        first_arrive = _parse_time_minutes(self.stops[0].arrive_at)
        if first_arrive < window_start:
            raise ValueError("first stop must not start before day_start")

        return self

    @property
    def poi_ids(self) -> list[str]:
        return [stop.poi_id for stop in self.stops]

    @property
    def stop_count(self) -> int:
        return len(self.stops)

    def to_timeline_context(self) -> str:
        """Compact timeline text for prompts or chat context."""
        if not self.stops:
            return "[周末行程] (空)"

        lines = [
            f"[周末行程 · {self.transport_mode} · {self.day_start}-{self.day_end}]"
        ]
        if self.warnings:
            lines.append("提示: " + "；".join(self.warnings))

        for index, stop in enumerate(self.stops):
            lines.append(
                f"{stop.order}. {stop.arrive_at}-{stop.leave_at} {stop.name} "
                f"(停留{stop.dwell_min}min)"
            )
            if index < len(self.legs):
                leg = self.legs[index]
                lines.append(
                    f"   → {leg.mode} {leg.duration_min}min / {leg.distance_m}m "
                    f"→ {self.stops[index + 1].name}"
                )

        lines.append(
            f"合计: 停留{self.total_dwell_min}min, 通勤{self.total_travel_min}min, "
            f"路程{self.total_distance_m}m"
        )
        return "\n".join(lines)


class BuildItineraryRequest(BaseModel):
    """API input for generating a weekend itinerary from selected POIs."""

    session_id: str = Field(default="default", min_length=1)
    poi_ids: list[str] = Field(
        min_length=MIN_ITINERARY_STOPS,
        max_length=MAX_ITINERARY_STOPS,
        description="POI ids selected from the current feed",
    )
    transport_mode: TransportMode = "walking"
    day_start: str = Field(default=DEFAULT_DAY_START)
    day_end: str = Field(default=DEFAULT_DAY_END)
    anchor_poi_id: str | None = Field(
        default=None,
        description="Optional POI id to start from; defaults to session anchor",
    )

    @field_validator("poi_ids")
    @classmethod
    def validate_poi_ids(cls, value: list[str]) -> list[str]:
        cleaned = [poi_id.strip() for poi_id in value if poi_id.strip()]
        if len(cleaned) < MIN_ITINERARY_STOPS:
            raise ValueError(f"at least {MIN_ITINERARY_STOPS} poi_id required")
        if len(cleaned) > MAX_ITINERARY_STOPS:
            raise ValueError(f"at most {MAX_ITINERARY_STOPS} poi_ids allowed")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("poi_ids must be unique")
        return cleaned

    @field_validator("day_start", "day_end")
    @classmethod
    def validate_day_bounds(cls, value: str) -> str:
        _parse_time_minutes(value)
        return value.strip()

    @model_validator(mode="after")
    def validate_day_window(self) -> Self:
        if _parse_time_minutes(self.day_end) <= _parse_time_minutes(self.day_start):
            raise ValueError("day_end must be after day_start")
        return self


class BuildItineraryResponse(BaseModel):
    """API output wrapping a generated itinerary."""

    itinerary: WeekendItinerary
    warnings: list[str] = Field(
        default_factory=list,
        description="Top-level planner warnings (also copied onto itinerary by the planner)",
    )
