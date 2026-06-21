"""Amap POI search tool for weekend travel planning."""

from __future__ import annotations

from typing import Literal, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, model_validator

from tools.amap_client import AmapClientError, AmapConfigError, get_amap_client
from tools.amap_tool_format import append_poi_json, format_poi_markdown


class AmapPoiSearchInput(BaseModel):
    keywords: str = Field(
        description="POI search keywords, e.g. 咖啡, 公园, 博物馆, 亲子"
    )
    city: str | None = Field(
        default=None,
        description="City name to limit search, e.g. 上海, 北京",
    )
    address: str | None = Field(
        default=None,
        description="Address used as search anchor when lng/lat are not provided",
    )
    lng: float | None = Field(
        default=None,
        description="Anchor longitude (GCJ-02) for nearby search",
    )
    lat: float | None = Field(
        default=None,
        description="Anchor latitude (GCJ-02) for nearby search",
    )
    radius: int = Field(
        default=3000,
        ge=100,
        le=50000,
        description="Nearby search radius in meters",
    )
    search_mode: Literal["auto", "nearby", "city"] = Field(
        default="auto",
        description="auto=prefer nearby when anchor exists, otherwise city keyword search",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=25,
        description="Maximum number of POI results",
    )

    @model_validator(mode="after")
    def validate_anchor(self) -> AmapPoiSearchInput:
        has_lng = self.lng is not None
        has_lat = self.lat is not None
        if has_lng ^ has_lat:
            raise ValueError("lng and lat must be provided together")
        return self


class AmapPoiSearchTool(BaseTool):
    name: str = "amap_search_poi"
    description: str = (
        "Search Amap POIs for weekend travel planning. "
        "Use for finding restaurants, attractions, parks, cafes, museums, and activities. "
        "Provide keywords plus either city, address, or lng/lat anchor for nearby search."
    )
    args_schema: Type[BaseModel] = AmapPoiSearchInput

    def _run(
        self,
        keywords: str,
        city: str | None = None,
        address: str | None = None,
        lng: float | None = None,
        lat: float | None = None,
        radius: int = 3000,
        search_mode: Literal["auto", "nearby", "city"] = "auto",
        limit: int = 10,
    ) -> str:
        try:
            client = get_amap_client()
            anchor_city = city
            anchor_lng, anchor_lat = lng, lat

            if address and (anchor_lng is None or anchor_lat is None):
                geocoded = client.geocode(address, city=city)
                anchor_lng = geocoded.lng
                anchor_lat = geocoded.lat
                anchor_city = geocoded.city or city
                address = geocoded.address or address

            use_nearby = search_mode == "nearby" or (
                search_mode == "auto" and anchor_lng is not None and anchor_lat is not None
            )

            if use_nearby:
                if anchor_lng is None or anchor_lat is None:
                    return (
                        "[FAIL] Nearby search requires lng/lat or address anchor. "
                        "Provide address, or lng+lat, or set search_mode='city'."
                    )
                pois = client.search_around(
                    anchor_lng,
                    anchor_lat,
                    keywords=keywords,
                    radius=radius,
                    offset=limit,
                    anchor_city=anchor_city,
                )
                title = (
                    f"Amap nearby POI search: {keywords} "
                    f"(anchor={anchor_lng},{anchor_lat}, radius={radius}m)"
                )
            else:
                pois = client.search_poi(
                    keywords,
                    city=city,
                    offset=limit,
                )
                title = f"Amap city POI search: {keywords}" + (
                    f" in {city}" if city else ""
                )

            markdown = format_poi_markdown(pois[:limit], title=title)
            if address and use_nearby:
                markdown = f"Anchor address: {address}\n\n{markdown}"
            return append_poi_json(markdown, pois[:limit])

        except AmapConfigError as exc:
            return f"[FAIL] {exc}"
        except AmapClientError as exc:
            return f"[FAIL] Amap POI search error: {exc}"
        except Exception as exc:
            return f"[FAIL] Unexpected POI search error: {exc}"


def create_amap_poi_tool() -> AmapPoiSearchTool:
    return AmapPoiSearchTool()
