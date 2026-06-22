#!/usr/bin/env python3
"""Tests for Parser Agent (Module C)."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from dotenv import load_dotenv

from domain import (
    GeoLocation,
    ParserInput,
    ParserOutput,
    PreferenceProfile,
    RecommendationFeed,
)
from graph.parser_agent import (
    ParserAgent,
    ParserValidationError,
    _coerce_parser_output,
    _extract_json_text,
    _finalize_output,
    _normalize_preference,
)

FIXTURE_FEED = Path(__file__).parent.parent / "domain" / "fixtures" / "sample_feed.json"

load_dotenv()


def test_extract_json_text_plain() -> None:
    payload = '{"preference": {}, "intent_summary": "ok", "confidence": "high"}'
    assert _extract_json_text(payload) == payload
    print("extract plain JSON OK")


def test_extract_json_text_markdown_fence() -> None:
    raw = '```json\n{"a": 1}\n```'
    assert _extract_json_text(raw) == '{"a": 1}'
    print("extract fenced JSON OK")


def test_normalize_preference_dedupes() -> None:
    pref = PreferenceProfile.empty()
    pref.positive_soft.tags = ["文艺", "文艺", " 亲子 "]
    normalized = _normalize_preference(pref)
    assert normalized.positive_soft.tags == ["文艺", "亲子"]
    print("normalize preference OK")


def test_finalize_output_sets_metadata() -> None:
    parser_input = ParserInput(command="3公里内", round=1)
    raw = ParserOutput(
        preference=PreferenceProfile.empty(
            anchor=GeoLocation(city="上海", address="静安寺")
        ),
        intent_summary="缩小半径",
    )
    output = _finalize_output(raw, parser_input)
    assert output.preference.source_command == "3公里内"
    assert output.preference.updated_at > 0
    assert output.preference.anchor is not None
    assert output.preference.anchor.city == "上海"
    print("finalize output OK")


def test_coerce_parser_output_from_dict() -> None:
    payload = {
        "preference": PreferenceProfile.empty().model_dump(mode="json"),
        "intent_summary": "测试",
        "confidence": "high",
    }
    output = _coerce_parser_output(payload)
    assert output.intent_summary == "测试"
    print("coerce from dict OK")


async def test_parse_with_mock_structured_llm() -> None:
    expected_pref = PreferenceProfile.empty(
        anchor=GeoLocation(city="上海", address=None)
    )
    expected_pref.positive_soft.tags = ["CityWalk", "文艺"]

    mock_structured_llm = MagicMock()
    mock_structured_llm.ainvoke = AsyncMock(
        return_value=ParserOutput(
            preference=expected_pref,
            intent_summary="上海 CityWalk 文艺出行",
            confidence="high",
        )
    )
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm

    agent = ParserAgent(llm=mock_llm)
    output = await agent.parse_command("这周末在上海想 CityWalk，文艺一点")

    assert output.preference.anchor is not None
    assert output.preference.anchor.city == "上海"
    assert "CityWalk" in output.preference.positive_soft.tags
    assert output.preference.source_command == "这周末在上海想 CityWalk，文艺一点"
    mock_llm.with_structured_output.assert_called_once()
    mock_structured_llm.ainvoke.assert_awaited_once()
    print("mock structured parse OK")


async def test_parse_retries_on_failure() -> None:
    good_pref = PreferenceProfile.empty()
    good_pref.positive_hard.radius_m = 3000

    failing_structured_llm = MagicMock()
    failing_structured_llm.ainvoke = AsyncMock(
        side_effect=ParserValidationError("bad json")
    )
    retry_structured_llm = MagicMock()
    retry_structured_llm.ainvoke = AsyncMock(
        return_value=ParserOutput(
            preference=good_pref,
            intent_summary="半径改为3公里",
        )
    )

    mock_llm = MagicMock()
    mock_llm.with_structured_output.side_effect = [
        failing_structured_llm,
        retry_structured_llm,
    ]

    agent = ParserAgent(llm=mock_llm)
    output = await agent.parse_command("3公里内")

    assert output.preference.positive_hard.radius_m == 3000
    assert mock_llm.with_structured_output.call_count == 2
    print("retry on failure OK")


async def _integration_cold_start() -> None:
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("SKIP integration: DEEPSEEK_API_KEY not set")
        return

    agent = ParserAgent()
    output = await agent.parse_command("这周末在上海想 CityWalk，文艺一点")

    assert output.preference.anchor is not None
    assert output.preference.anchor.city == "上海"
    tags = output.preference.positive_soft.tags
    assert any("CityWalk" in tag or "citywalk" in tag.lower() for tag in tags) or any(
        "文艺" in tag for tag in tags
    )
    assert output.intent_summary
    print("integration cold start OK:", output.intent_summary)


async def _integration_tighten_constraints() -> None:
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("SKIP integration tighten: DEEPSEEK_API_KEY not set")
        return

    feed = RecommendationFeed.model_validate_json(
        FIXTURE_FEED.read_text(encoding="utf-8")
    )
    agent = ParserAgent()
    output = await agent.parse_command(
        "3公里内，人均80以内，别去商场",
        preference=feed.preference_snapshot,
        round=2,
    )

    assert output.preference.positive_hard.radius_m == 3000
    assert output.preference.positive_hard.max_price == 80
    assert "商场" in output.preference.negative_hard.exclude_categories
    assert "文艺" in output.preference.positive_soft.tags
    print("integration tighten OK:", json.dumps(output.model_dump(mode="json"), ensure_ascii=False)[:200])


def test_integration_cold_start() -> None:
    asyncio.run(_integration_cold_start())


def test_integration_tighten_constraints() -> None:
    asyncio.run(_integration_tighten_constraints())


if __name__ == "__main__":
    test_extract_json_text_plain()
    test_extract_json_text_markdown_fence()
    test_normalize_preference_dedupes()
    test_finalize_output_sets_metadata()
    test_coerce_parser_output_from_dict()
    asyncio.run(test_parse_with_mock_structured_llm())
    asyncio.run(test_parse_retries_on_failure())
    test_integration_cold_start()
    test_integration_tighten_constraints()
    print("ALL MODULE C TESTS PASSED")
