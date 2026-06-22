#!/usr/bin/env python3
"""Tests for Parser prompt assembly (Module B)."""

import json
from pathlib import Path

from domain import (
    GeoLocation,
    IRFSessionState,
    ParserInput,
    PreferenceProfile,
    RecommendationFeed,
)
from graph.parser_prompt import (
    PARSER_SYSTEM_PATH,
    PARSER_USER_TEMPLATE_PATH,
    build_parser_messages,
    build_parser_user_prompt,
    load_parser_system_prompt,
    load_parser_user_template,
)

FIXTURE_FEED = Path(__file__).parent / "domain" / "fixtures" / "sample_feed.json"


def test_prompt_files_exist() -> None:
    assert PARSER_SYSTEM_PATH.is_file()
    assert PARSER_USER_TEMPLATE_PATH.is_file()
    print("prompt files exist OK")


def test_system_prompt_sections() -> None:
    system = load_parser_system_prompt(truncate=False)
    required = [
        "四象限映射表",
        "动态记忆合并三原则",
        "负向硬排除 vs 负向软惩罚",
        "锚点解析规则",
        "Few-shot 示例",
        "positive_hard",
        "negative_soft",
        "intent_summary",
        "confidence",
    ]
    for section in required:
        assert section in system, f"missing section: {section}"
    print("system prompt sections OK")


def test_user_template_placeholders_replaced() -> None:
    feed = RecommendationFeed.model_validate_json(
        FIXTURE_FEED.read_text(encoding="utf-8")
    )
    parser_input = ParserInput(
        command="3公里内，别去商场",
        round=2,
        preference=feed.preference_snapshot,
        feed=feed,
        command_history=["上一轮：文艺 CityWalk"],
    )
    user_prompt = build_parser_user_prompt(parser_input)

    assert "{{" not in user_prompt, "unreplaced template placeholders"
    assert "第 2 轮" in user_prompt
    assert "3公里内，别去商场" in user_prompt
    assert "武康路历史文化名街" in user_prompt
    assert "半径5000m" in user_prompt
    assert "上一轮：文艺 CityWalk" in user_prompt
    print("user prompt rendering OK:\n", user_prompt[:400], "...")


def test_cold_start_user_prompt() -> None:
    parser_input = ParserInput(
        command="上海周末想喝咖啡",
        round=1,
        preference=PreferenceProfile.empty(),
        feed=None,
    )
    user_prompt = build_parser_user_prompt(parser_input)
    assert "尚无推荐结果" in user_prompt
    assert "空白偏好" in user_prompt
    assert "无历史命令" in user_prompt
    print("cold start user prompt OK")


def test_build_parser_messages() -> None:
    parser_input = ParserInput(
        command="人均100以内",
        round=1,
        preference=PreferenceProfile.empty(
            anchor=GeoLocation(city="上海", address="静安寺")
        ),
    )
    messages = build_parser_messages(parser_input)
    assert len(messages) == 2
    assert messages[0].type == "system"
    assert messages[1].type == "human"
    assert "Parser Agent" in messages[0].content
    assert "人均100以内" in messages[1].content
    assert "静安寺" in messages[1].content
    print("build_parser_messages OK")


def test_system_prompt_mentions_optional_coords() -> None:
    system = load_parser_system_prompt()
    assert "lng" in system and "lat" in system
    assert "null" in system
    assert "geocode" in system.lower() or "Planner" in system
    print("optional coords guidance OK")


def test_user_template_has_all_keys() -> None:
    template = load_parser_user_template()
    for key in ("round", "command", "preference_context", "feed_context", "history_context"):
        assert f"{{{{{key}}}}}" in template
    print("user template keys OK")


def test_messages_serializable_length() -> None:
    """Sanity check: prompt bundle should stay within reasonable token budget."""
    feed = RecommendationFeed.model_validate_json(
        FIXTURE_FEED.read_text(encoding="utf-8")
    )
    state = IRFSessionState(current_feed=feed, preference=feed.preference_snapshot)
    parser_input = state.build_parser_input("第2个不错，类似的再多推荐")
    messages = build_parser_messages(parser_input)
    total_chars = sum(len(m.content) for m in messages)
    assert total_chars < 20000, f"prompt too long: {total_chars} chars"
    payload = [{"role": m.type, "len": len(m.content)} for m in messages]
    print("prompt size OK:", json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    test_prompt_files_exist()
    test_system_prompt_sections()
    test_user_template_placeholders_replaced()
    test_cold_start_user_prompt()
    test_build_parser_messages()
    test_system_prompt_mentions_optional_coords()
    test_user_template_has_all_keys()
    test_messages_serializable_length()
    print("ALL MODULE B TESTS PASSED")
