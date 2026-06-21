"""Amap weather query tool for weekend travel planning."""

from __future__ import annotations

from typing import Literal, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from tools.amap_client import AmapClientError, AmapConfigError, get_amap_client
from tools.amap_tool_format import format_weather_markdown


class AmapWeatherInput(BaseModel):
    city: str = Field(
        description="City name or adcode for weather query, e.g. 上海 or 310101"
    )
    extensions: Literal["base", "all"] = Field(
        default="all",
        description="base=current weather only, all=current plus forecast",
    )


class AmapWeatherTool(BaseTool):
    name: str = "amap_weather"
    description: str = (
        "Query Amap weather by city name or adcode. "
        "Use before recommending outdoor activities to check rain, temperature, and forecast."
    )
    args_schema: Type[BaseModel] = AmapWeatherInput

    def _run(
        self,
        city: str,
        extensions: Literal["base", "all"] = "all",
    ) -> str:
        try:
            client = get_amap_client()
            info = client.weather(city, extensions=extensions)
            return format_weather_markdown(info)
        except AmapConfigError as exc:
            return f"[FAIL] {exc}"
        except AmapClientError as exc:
            return f"[FAIL] Amap weather error: {exc}"
        except Exception as exc:
            return f"[FAIL] Unexpected weather error: {exc}"


def create_amap_weather_tool() -> AmapWeatherTool:
    return AmapWeatherTool()
