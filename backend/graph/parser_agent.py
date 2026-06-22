"""Parser Agent — natural language command to structured preference P_{t+1}."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage

from domain.feed import RecommendationFeed
from domain.irf_state import ParserInput, ParserOutput
from domain.preference import PreferenceProfile
from graph.parser_prompt import build_parser_messages

logger = logging.getLogger(__name__)

MAX_PARSE_ATTEMPTS = 2


class ParserAgentError(Exception):
    """Base error for Parser Agent failures."""


class ParserValidationError(ParserAgentError):
    """Raised when LLM output cannot be validated as ParserOutput."""


def _extract_json_text(content: str) -> str:
    """Pull a JSON object from raw LLM text (strip markdown fences if present)."""
    stripped = content.strip()
    if not stripped:
        raise ParserValidationError("empty LLM response")

    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped, re.IGNORECASE)
    if fence_match:
        stripped = fence_match.group(1).strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ParserValidationError("no JSON object found in LLM response")
    return stripped[start : end + 1]


def _coerce_parser_output(value: Any) -> ParserOutput:
    """Normalize structured-output or raw LLM payload to ParserOutput."""
    if isinstance(value, ParserOutput):
        return value
    if isinstance(value, dict):
        return ParserOutput.model_validate(value)
    if isinstance(value, str):
        return ParserOutput.model_validate(json.loads(_extract_json_text(value)))
    raise ParserValidationError(f"unexpected parser payload type: {type(value)!r}")


def _normalize_preference(preference: PreferenceProfile) -> PreferenceProfile:
    """Strip and deduplicate list fields after LLM generation."""
    positive_hard = preference.positive_hard.model_copy(
        update={
            "categories": PreferenceProfile._merge_unique(
                [], preference.positive_hard.categories
            ),
        }
    )
    positive_soft = preference.positive_soft.model_copy(
        update={
            "tags": PreferenceProfile._merge_unique([], preference.positive_soft.tags),
            "keywords": PreferenceProfile._merge_unique(
                [], preference.positive_soft.keywords
            ),
            "cuisine_types": PreferenceProfile._merge_unique(
                [], preference.positive_soft.cuisine_types
            ),
        }
    )
    negative_hard = preference.negative_hard.model_copy(
        update={
            "exclude_categories": PreferenceProfile._merge_unique(
                [], preference.negative_hard.exclude_categories
            ),
            "exclude_poi_ids": PreferenceProfile._merge_unique(
                [], preference.negative_hard.exclude_poi_ids
            ),
            "exclude_tags": PreferenceProfile._merge_unique(
                [], preference.negative_hard.exclude_tags
            ),
        }
    )
    negative_soft = preference.negative_soft.model_copy(
        update={
            "dislike_tags": PreferenceProfile._merge_unique(
                [], preference.negative_soft.dislike_tags
            ),
            "dislike_keywords": PreferenceProfile._merge_unique(
                [], preference.negative_soft.dislike_keywords
            ),
        }
    )
    return preference.model_copy(
        update={
            "positive_hard": positive_hard,
            "positive_soft": positive_soft,
            "negative_hard": negative_hard,
            "negative_soft": negative_soft,
        }
    )


def _finalize_output(raw: ParserOutput, parser_input: ParserInput) -> ParserOutput:
    """Attach command metadata and normalize preference lists."""
    preference = _normalize_preference(raw.preference)
    preference = preference.model_copy(
        update={
            "source_command": parser_input.command,
            "updated_at": time.time(),
        }
    )
    return raw.model_copy(update={"preference": preference})


class ParserAgent:
    """Single-turn LLM parser: (R_t, c_t, P_t) -> P_{t+1}."""

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    def _build_llm(self) -> Any:
        from langchain_deepseek import ChatDeepSeek

        return ChatDeepSeek(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            api_base=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            temperature=0.2,
            streaming=False,
        )

    def _get_llm(self) -> Any:
        return self._llm or self._build_llm()

    async def _invoke_structured(
        self, messages: list[BaseMessage]
    ) -> ParserOutput:
        """Primary path: LangChain structured output."""
        structured_llm = self._get_llm().with_structured_output(ParserOutput)
        result = await structured_llm.ainvoke(messages)
        return _coerce_parser_output(result)

    async def _invoke_raw_json(self, messages: list[BaseMessage]) -> ParserOutput:
        """Fallback path: free-form JSON response + manual validation."""
        result = await self._get_llm().ainvoke(messages)
        content = getattr(result, "content", None)
        if not isinstance(content, str):
            raise ParserValidationError("LLM response has no text content")
        return _coerce_parser_output(content)

    async def _invoke_with_retry_hint(
        self,
        messages: list[BaseMessage],
        error: Exception,
    ) -> ParserOutput:
        """Second attempt with explicit correction hint."""
        retry_messages = list(messages) + [
            HumanMessage(
                content=(
                    "上次输出无法解析为合法 JSON 或字段校验失败。\n"
                    f"错误: {error}\n"
                    "请严格输出一个 JSON 对象，包含 preference、intent_summary、"
                    "confidence 三个顶层字段，不要 markdown 代码块或额外解释。"
                )
            )
        ]
        try:
            return await self._invoke_structured(retry_messages)
        except Exception:
            return await self._invoke_raw_json(retry_messages)

    async def parse(
        self,
        parser_input: ParserInput,
        *,
        max_feed_items: int = 5,
    ) -> ParserOutput:
        """Parse user command into complete P_{t+1}."""
        messages = build_parser_messages(
            parser_input,
            max_feed_items=max_feed_items,
        )
        last_error: Exception | None = None

        for attempt in range(MAX_PARSE_ATTEMPTS):
            try:
                if attempt == 0:
                    raw = await self._invoke_structured(messages)
                else:
                    assert last_error is not None
                    raw = await self._invoke_with_retry_hint(messages, last_error)

                output = _finalize_output(raw, parser_input)
                if output.confidence == "low":
                    logger.warning(
                        "Parser low confidence for command %r: %s",
                        parser_input.command,
                        output.intent_summary,
                    )
                return output
            except Exception as exc:
                last_error = exc
                logger.debug(
                    "Parser attempt %d failed: %s",
                    attempt + 1,
                    exc,
                    exc_info=True,
                )

        raise ParserAgentError(
            f"Parser failed after {MAX_PARSE_ATTEMPTS} attempts: {last_error}"
        ) from last_error

    async def parse_command(
        self,
        command: str,
        *,
        preference: PreferenceProfile | None = None,
        feed: RecommendationFeed | None = None,
        round: int = 1,
        command_history: list[str] | None = None,
        max_feed_items: int = 5,
    ) -> ParserOutput:
        """Convenience wrapper that builds ParserInput internally."""
        parser_input = ParserInput(
            command=command,
            round=round,
            preference=preference or PreferenceProfile.empty(),
            feed=feed,
            command_history=command_history or [],
        )
        return await self.parse(parser_input, max_feed_items=max_feed_items)


parser_agent = ParserAgent()
