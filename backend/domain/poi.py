"""POI item model and Amap response normalization."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from domain.types import GeoLocation


def _parse_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_cost_numeric(cost: str | None) -> float | None:
    if not cost:
        return None
    match = re.search(r"[\d.]+", cost)
    if not match:
        return None
    return _parse_optional_float(match.group())


def _split_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[;；,，|/]", raw)
    return [part.strip() for part in parts if part.strip()]


class POIItem(BaseModel):
    """Normalized POI item used as recommendation candidate I."""

    id: str = Field(description="Amap POI id")
    name: str
    type: str = Field(description="Amap type string, e.g. 咖啡厅;星巴克")
    typecode: str | None = Field(default=None, description="Amap type code")
    address: str = Field(default="")
    location: GeoLocation
    rating: float | None = Field(default=None, ge=0, le=5)
    cost: str | None = Field(default=None, description="Raw cost text from Amap")
    cost_numeric: float | None = Field(
        default=None,
        ge=0,
        description="Parsed average cost per person (CNY)",
    )
    distance_m: float | None = Field(
        default=None,
        ge=0,
        description="Distance to search anchor in meters",
    )
    tel: str | None = None
    tags: list[str] = Field(default_factory=list)
    description: str = Field(
        default="",
        description="Text summary for semantic matching / embedding",
    )
    photos: list[str] = Field(default_factory=list)
    raw: dict[str, Any] | None = Field(
        default=None,
        description="Original Amap POI payload for debugging",
    )

    @field_validator("id", "name")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("field cannot be empty")
        return normalized

    @classmethod
    def build_description(
        cls,
        *,
        name: str,
        type: str,
        address: str = "",
        tags: list[str] | None = None,
        rating: float | None = None,
        cost: str | None = None,
        city: str | None = None,
    ) -> str:
        """Compose a stable text description for Matcher embedding."""
        parts = [name, type]
        if address:
            parts.append(address)
        if city:
            parts.append(city)
        if tags:
            parts.extend(tags)
        if rating is not None:
            parts.append(f"评分{rating}")
        if cost:
            parts.append(cost)
        return " ".join(part.strip() for part in parts if part and str(part).strip())

    def refresh_description(self) -> None:
        self.description = self.build_description(
            name=self.name,
            type=self.type,
            address=self.address,
            tags=self.tags,
            rating=self.rating,
            cost=self.cost,
            city=self.location.city,
        )


def parse_amap_poi(
    raw: dict[str, Any],
    *,
    anchor_city: str | None = None,
    keep_raw: bool = True,
) -> POIItem:
    """Normalize a single Amap POI dict into ``POIItem``."""
    poi_id = str(raw.get("id", "")).strip()
    name = str(raw.get("name", "")).strip()
    if not poi_id or not name:
        raise ValueError("Amap POI must contain non-empty id and name")

    location_raw = raw.get("location")
    if not location_raw:
        raise ValueError(f"POI {poi_id} missing location")
    location = GeoLocation.from_amap_location(
        str(location_raw),
        city=anchor_city,
    )

    biz_ext = raw.get("biz_ext") or {}
    if not isinstance(biz_ext, dict):
        biz_ext = {}

    rating = _parse_optional_float(biz_ext.get("rating"))
    cost = biz_ext.get("cost")
    cost_text = str(cost).strip() if cost not in (None, "") else None
    cost_numeric = _parse_cost_numeric(cost_text)

    type_text = str(raw.get("type", "")).strip()
    typecode = str(raw.get("typecode", "")).strip() or None
    address = str(raw.get("address", "")).strip()
    tel = str(raw.get("tel", "")).strip() or None
    distance_m = _parse_optional_float(raw.get("distance"))

    tags = _split_tags(raw.get("tag"))
    if not tags and type_text:
        tags = _split_tags(type_text)

    photos: list[str] = []
    photo_field = raw.get("photos")
    if isinstance(photo_field, list):
        for photo in photo_field:
            if isinstance(photo, dict) and photo.get("url"):
                photos.append(str(photo["url"]))

    description = POIItem.build_description(
        name=name,
        type=type_text,
        address=address,
        tags=tags,
        rating=rating,
        cost=cost_text,
        city=anchor_city,
    )

    return POIItem(
        id=poi_id,
        name=name,
        type=type_text,
        typecode=typecode,
        address=address,
        location=location,
        rating=rating,
        cost=cost_text,
        cost_numeric=cost_numeric,
        distance_m=distance_m,
        tel=tel,
        tags=tags,
        description=description,
        photos=photos,
        raw=raw if keep_raw else None,
    )


def parse_amap_pois(
    pois: list[dict[str, Any]],
    *,
    anchor_city: str | None = None,
    keep_raw: bool = True,
) -> list[POIItem]:
    """Normalize a list of Amap POI dicts, skipping invalid entries."""
    items: list[POIItem] = []
    for raw in pois:
        try:
            items.append(
                parse_amap_poi(
                    raw,
                    anchor_city=anchor_city,
                    keep_raw=keep_raw,
                )
            )
        except ValueError:
            continue
    return items
