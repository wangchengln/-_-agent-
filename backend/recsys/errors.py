"""IRF error codes and user-facing messages (Day 4.5)."""

from __future__ import annotations

MAX_COMMAND_LENGTH = 500

# Stable codes consumed by the front-end; do not rename without a migration.
ERROR_CODES = frozenset(
    {
        "invalid_command",
        "parse_failed",
        "anchor_missing",
        "empty_pool",
        "internal_error",
    }
)

ERROR_MESSAGES: dict[str, str] = {
    "invalid_command": "指令不能为空，且请控制在合理长度内。",
    "parse_failed": "无法理解这条指令，请换种说法再试。",
    "anchor_missing": "还不知道你想在哪一带玩，告诉我城市或大致地点吧。",
    "empty_pool": "这一带没找到合适的去处，试试放宽距离或更换区域。",
    "internal_error": "推荐服务暂时出错，请稍后再试。",
}

RETRY_HINTS: dict[str, str] = {
    "invalid_command": "例如：「上海周末想找个文艺的咖啡馆」",
    "parse_failed": "可以说得更具体一些，比如地点、氛围或预算。",
    "anchor_missing": "例如：「徐汇区附近」「杭州西湖边」",
    "empty_pool": "试试：「距离远一点也行」或换一个区域。",
    "internal_error": "稍后重试；若持续失败请检查网络与 API 配置。",
}

LOW_CONFIDENCE_HINT = "我理解得还不太准，如果结果不对请补充说明。"


def normalize_command(command: str) -> tuple[str | None, str | None]:
    """Validate and strip a user command.

    Returns ``(normalized, error_code)``. *error_code* is set when invalid.
    """
    stripped = command.strip()
    if not stripped:
        return None, "invalid_command"
    if len(stripped) > MAX_COMMAND_LENGTH:
        return None, "invalid_command"
    return stripped, None


def error_message(code: str, *, detail: str | None = None) -> str:
    """Resolve a user-facing message for *code*."""
    base = ERROR_MESSAGES.get(code, ERROR_MESSAGES["internal_error"])
    if detail and code == "internal_error":
        return f"{base}（{detail}）"
    return base
