"""Weather snapshot attached to a recommendation feed (Day 6.2)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WeatherSnapshot(BaseModel):
    """Normalized weather context for one IRF scoring round."""

    city: str = Field(default="", description="City name from Amap")
    adcode: str = Field(default="", description="Administrative region code")
    summary: str = Field(
        default="",
        description="Short weather text, e.g. 小雨 / 晴",
    )
    temperature: str | None = Field(
        default=None,
        description="Current temperature string from Amap",
    )
    is_rainy: bool = Field(
        default=False,
        description="Heuristic: rain/snow/thunder likely",
    )
    injected_rule: str | None = Field(
        default=None,
        description="Human-readable rule applied to scoring, if any",
    )
    fetched: bool = Field(
        default=True,
        description="False when weather lookup was skipped or failed",
    )
