"""POI detail view model for Phase 2 detail page."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PoiReview(BaseModel):
    """One user review sourced from Amap comment service."""

    id: str | None = None
    author: str = Field(default="匿名用户")
    rating: float | None = Field(default=None, ge=0, le=5)
    content: str = ""
    created_at: str | None = None
    photos: list[str] = Field(default_factory=list)
    source: str = Field(default="amap", description="Review data provider")


class PoiDetail(BaseModel):
    """Enriched POI payload for the detail page."""

    poi_id: str
    name: str
    type: str = ""
    address: str = ""
    lng: float | None = None
    lat: float | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    cost: str | None = None
    tel: str | None = None
    open_time: str | None = None
    website: str | None = None
    tags: list[str] = Field(default_factory=list)
    photos: list[str] = Field(default_factory=list)
    distance_m: float | None = Field(default=None, ge=0)
    score: float | None = None
    rank: int | None = Field(default=None, ge=1)
    reason: str | None = Field(default=None, description="IRF recommendation reason")
    reviews: list[PoiReview] = Field(default_factory=list)
    reviews_total: int | None = Field(default=None, ge=0)
    reviews_fetched: bool = False
    reviews_source: str = Field(
        default="amap",
        description="amap | unavailable",
    )
