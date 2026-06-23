"""Itinerary planner error codes and messages (Day 6.4)."""

from __future__ import annotations

ITINERARY_ERROR_CODES = frozenset(
    {
        "no_feed",
        "poi_not_found",
        "missing_coords",
        "invalid_anchor_poi",
        "internal_error",
    }
)

ITINERARY_ERROR_MESSAGES: dict[str, str] = {
    "no_feed": "当前会话还没有推荐结果，请先发起一轮推荐。",
    "poi_not_found": "所选 POI 不在当前推荐 feed 中，请从最新推荐里选择。",
    "missing_coords": "部分 POI 或锚点缺少坐标，无法规划路线。",
    "invalid_anchor_poi": "指定的起点 POI 不在已选列表中。",
    "internal_error": "行程规划暂时出错，请稍后再试。",
}


class ItineraryPlannerError(Exception):
    """Recoverable itinerary planning failure with a stable error code."""

    def __init__(
        self,
        code: str,
        message: str | None = None,
        *,
        detail: str | None = None,
    ) -> None:
        if code not in ITINERARY_ERROR_CODES:
            code = "internal_error"
        base = message or ITINERARY_ERROR_MESSAGES.get(code, ITINERARY_ERROR_MESSAGES["internal_error"])
        if detail:
            base = f"{base}（{detail}）"
        super().__init__(base)
        self.code = code
        self.message = base


def itinerary_error_message(code: str, *, detail: str | None = None) -> str:
    base = ITINERARY_ERROR_MESSAGES.get(code, ITINERARY_ERROR_MESSAGES["internal_error"])
    if detail and code == "internal_error":
        return f"{base}（{detail}）"
    return base
