"""Shared domain types for the weekend travel recommendation system."""

from __future__ import annotations

from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, field_validator


class VenueType(str, Enum):
    """Indoor/outdoor venue preference."""

    ANY = "any"
    INDOOR = "indoor"
    OUTDOOR = "outdoor"


class GeoLocation(BaseModel):
    """Geographic anchor used for POI search and distance filtering."""

    lng: float = Field(description="Longitude (GCJ-02)")
    lat: float = Field(description="Latitude (GCJ-02)")
    city: str | None = Field(default=None, description="City name, e.g. 上海")
    adcode: str | None = Field(default=None, description="Administrative region code")
    address: str | None = Field(
        default=None, description="Human-readable anchor address"
    )

    @field_validator("lng")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if not (-180.0 <= value <= 180.0):
            raise ValueError("longitude must be between -180 and 180")
        return value

    @field_validator("lat")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if not (-90.0 <= value <= 90.0):
            raise ValueError("latitude must be between -90 and 90")
        return value

    @classmethod
    def from_amap_location(cls, location: str, **kwargs) -> Self:
        """Parse Amap location string ``'lng,lat'``."""
        parts = [part.strip() for part in location.split(",")]
        if len(parts) != 2:
            raise ValueError(f"invalid Amap location string: {location!r}")
        lng, lat = float(parts[0]), float(parts[1])
        if not (-90.0 <= lat <= 90.0):
            raise ValueError("latitude must be between -90 and 90")
        return cls(lng=lng, lat=lat, **kwargs)

    def to_amap_location(self) -> str:
        return f"{self.lng},{self.lat}"
