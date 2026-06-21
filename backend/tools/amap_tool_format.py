"""Format helpers shared by Amap LangChain tools."""

from __future__ import annotations

import json

from domain.poi import POIItem
from tools.amap_client import RoutePlan, WeatherInfo


def format_poi_markdown(pois: list[POIItem], *, title: str) -> str:
    lines = [title, ""]
    if not pois:
        lines.append("No POI results found.")
        return "\n".join(lines)

    for index, poi in enumerate(pois, start=1):
        distance = f"{poi.distance_m:.0f}m" if poi.distance_m is not None else "N/A"
        rating = poi.rating if poi.rating is not None else "N/A"
        cost = poi.cost or "N/A"
        lines.extend(
            [
                f"**{index}. {poi.name}** (id={poi.id})",
                f"   Type: {poi.type}",
                f"   Address: {poi.address or 'N/A'}",
                f"   Location: {poi.location.to_amap_location()}",
                f"   Distance: {distance} | Rating: {rating} | Cost: {cost}",
            ]
        )
        if poi.tags:
            lines.append(f"   Tags: {', '.join(poi.tags)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def append_poi_json(markdown: str, pois: list[POIItem]) -> str:
    payload = [poi.model_dump(mode="json") for poi in pois]
    json_block = json.dumps(payload, ensure_ascii=False, indent=2)
    return f"{markdown}\n\n---\nStructured POI JSON:\n```json\n{json_block}\n```"


def format_weather_markdown(info: WeatherInfo) -> str:
    lines = ["Weather query result", ""]
    if info.lives:
        live = info.lives[0]
        lines.extend(
            [
                f"City: {live.city or info.city}",
                f"Adcode: {live.adcode or info.adcode}",
                f"Current: {live.weather} {live.temperature}C",
                f"Wind: {live.winddirection} {live.windpower}",
                f"Humidity: {live.humidity}%",
                f"Report time: {live.reporttime or info.reporttime}",
                f"Rainy heuristic: {info.is_rainy}",
                "",
            ]
        )
    if info.casts:
        lines.append("Forecast:")
        for cast in info.casts[:4]:
            lines.append(
                f"- {cast.date}: day {cast.dayweather} {cast.daytemp}C, "
                f"night {cast.nightweather} {cast.nighttemp}C"
            )
    return "\n".join(lines).rstrip()


def format_route_markdown(route: RoutePlan) -> str:
    minutes = route.duration_s // 60 if route.duration_s else 0
    lines = [
        "Route planning result",
        "",
        f"Mode: {route.mode}",
        f"Distance: {route.distance_m}m",
        f"Duration: {route.duration_s}s (~{minutes} min)",
        f"Origin: {route.origin.to_amap_location()}",
        f"Destination: {route.destination.to_amap_location()}",
        "",
        "Steps:",
    ]
    for index, step in enumerate(route.steps[:8], start=1):
        instruction = step.instruction.replace("\n", " ").strip()
        lines.append(
            f"{index}. {instruction} ({step.distance_m}m, {step.duration_s}s)"
        )
    if len(route.steps) > 8:
        lines.append(f"... and {len(route.steps) - 8} more steps")
    return "\n".join(lines)
