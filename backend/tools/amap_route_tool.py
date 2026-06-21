"""Amap route planning tool for weekend travel planning."""

from __future__ import annotations

from typing import Literal, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, model_validator

from domain.types import GeoLocation
from tools.amap_client import AmapClientError, AmapConfigError, get_amap_client
from tools.amap_tool_format import format_route_markdown


class AmapRoutePlanInput(BaseModel):
    origin_lng: float | None = Field(
        default=None,
        description="Origin longitude (GCJ-02)",
    )
    origin_lat: float | None = Field(
        default=None,
        description="Origin latitude (GCJ-02)",
    )
    dest_lng: float | None = Field(
        default=None,
        description="Destination longitude (GCJ-02)",
    )
    dest_lat: float | None = Field(
        default=None,
        description="Destination latitude (GCJ-02)",
    )
    origin_address: str | None = Field(
        default=None,
        description="Origin address; used when origin lng/lat are absent",
    )
    dest_address: str | None = Field(
        default=None,
        description="Destination address; used when destination lng/lat are absent",
    )
    mode: Literal["walking", "driving", "transit"] = Field(
        default="walking",
        description="Route mode: walking, driving, or transit",
    )
    city: str | None = Field(
        default=None,
        description="City name required for transit and helpful for geocoding",
    )

    @model_validator(mode="after")
    def validate_endpoints(self) -> AmapRoutePlanInput:
        has_origin_coords = self.origin_lng is not None and self.origin_lat is not None
        has_dest_coords = self.dest_lng is not None and self.dest_lat is not None
        has_origin_address = bool(self.origin_address)
        has_dest_address = bool(self.dest_address)

        if not has_origin_coords and not has_origin_address:
            raise ValueError("origin requires origin_lng/origin_lat or origin_address")
        if not has_dest_coords and not has_dest_address:
            raise ValueError(
                "destination requires dest_lng/dest_lat or dest_address"
            )

        if (self.origin_lng is None) ^ (self.origin_lat is None):
            raise ValueError("origin_lng and origin_lat must be provided together")
        if (self.dest_lng is None) ^ (self.dest_lat is None):
            raise ValueError("dest_lng and dest_lat must be provided together")
        if self.mode == "transit" and not self.city:
            raise ValueError("city is required when mode='transit'")
        return self


class AmapRoutePlanTool(BaseTool):
    name: str = "amap_route_plan"
    description: str = (
        "Plan a route using Amap for walking, driving, or public transit. "
        "Use when estimating travel time/distance between two places in a weekend plan."
    )
    args_schema: Type[BaseModel] = AmapRoutePlanInput

    @staticmethod
    def _resolve_location(
        client,
        *,
        lng: float | None,
        lat: float | None,
        address: str | None,
        city: str | None,
        label: str,
    ) -> GeoLocation:
        if lng is not None and lat is not None:
            return GeoLocation(lng=lng, lat=lat, city=city)
        if not address:
            raise ValueError(f"{label} coordinates or address is required")
        return client.geocode(address, city=city)

    def _run(
        self,
        origin_lng: float | None = None,
        origin_lat: float | None = None,
        dest_lng: float | None = None,
        dest_lat: float | None = None,
        origin_address: str | None = None,
        dest_address: str | None = None,
        mode: Literal["walking", "driving", "transit"] = "walking",
        city: str | None = None,
    ) -> str:
        try:
            client = get_amap_client()
            origin = self._resolve_location(
                client,
                lng=origin_lng,
                lat=origin_lat,
                address=origin_address,
                city=city,
                label="origin",
            )
            destination = self._resolve_location(
                client,
                lng=dest_lng,
                lat=dest_lat,
                address=dest_address,
                city=city,
                label="destination",
            )

            if mode == "walking":
                route = client.plan_walking_route(origin, destination)
            elif mode == "driving":
                route = client.plan_driving_route(origin, destination)
            else:
                route = client.plan_transit_route(
                    origin,
                    destination,
                    city=city or origin.city or destination.city or "",
                )

            return format_route_markdown(route)

        except AmapConfigError as exc:
            return f"[FAIL] {exc}"
        except AmapClientError as exc:
            return f"[FAIL] Amap route planning error: {exc}"
        except ValueError as exc:
            return f"[FAIL] {exc}"
        except Exception as exc:
            return f"[FAIL] Unexpected route planning error: {exc}"


def create_amap_route_tool() -> AmapRoutePlanTool:
    return AmapRoutePlanTool()
