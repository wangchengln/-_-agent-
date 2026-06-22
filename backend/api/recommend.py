"""POST /api/recommend — SSE streaming IRF recommendation loop."""

from __future__ import annotations

import json
import traceback
from typing import Any, AsyncGenerator

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator
from sse_starlette.sse import EventSourceResponse

from recsys.errors import MAX_COMMAND_LENGTH, normalize_command
from recsys.loop import IRFLoop, LoopEvent, irf_loop

router = APIRouter()


class RecommendRequest(BaseModel):
    command: str = Field(description="Natural language command c_t")
    session_id: str = "default"
    stream: bool = True
    k: int | None = Field(
        default=None,
        ge=1,
        description="Top-K feed size; defaults to scoring pipeline config",
    )

    @field_validator("command")
    @classmethod
    def validate_command(cls, value: str) -> str:
        normalized, error_code = normalize_command(value)
        if error_code is not None:
            if not value.strip():
                raise ValueError("command must not be empty")
            raise ValueError(
                f"command must be at most {MAX_COMMAND_LENGTH} characters"
            )
        return normalized


def loop_event_to_sse(event: LoopEvent) -> dict[str, str] | list[dict[str, str]]:
    """Map a :class:`LoopEvent` to one or more SSE wire frames.

    ``stage`` events are expanded into ``tool_start`` / ``tool_end`` so the
    existing front-end ThoughtChain can reuse the chat SSE handlers.
    """
    payload = event.payload

    if event.type == "stage":
        name = payload.get("name", "planner")
        status = payload.get("status")
        if status == "start":
            return {
                "event": "tool_start",
                "data": json.dumps({"tool": name, "input": {}}, ensure_ascii=False),
            }
        return {
            "event": "tool_end",
            "data": json.dumps({"tool": name, "output": {}}, ensure_ascii=False),
        }

    return {
        "event": event.type,
        "data": json.dumps(payload, ensure_ascii=False),
    }


async def event_generator(
    command: str,
    session_id: str,
    *,
    k: int | None = None,
    loop: IRFLoop | None = None,
) -> AsyncGenerator[dict[str, str], None]:
    """Stream SSE events from one IRF round."""
    runner = loop or irf_loop
    try:
        async for event in runner.run_round(session_id, command, k=k):
            mapped = loop_event_to_sse(event)
            if isinstance(mapped, list):
                for frame in mapped:
                    yield frame
            else:
                yield mapped
    except Exception as exc:
        traceback.print_exc()
        yield {
            "event": "error",
            "data": json.dumps(
                {"code": "internal_error", "message": str(exc)},
                ensure_ascii=False,
            ),
        }


async def collect_round_result(
    command: str,
    session_id: str,
    *,
    k: int | None = None,
    loop: IRFLoop | None = None,
) -> dict[str, Any]:
    """Run one round and aggregate events for non-streaming clients."""
    result: dict[str, Any] = {
        "session_id": session_id,
        "command": command,
    }
    tokens: list[str] = []

    async for event in (loop or irf_loop).run_round(session_id, command, k=k):
        if event.type == "intent":
            result["intent_summary"] = event.payload.get("intent_summary")
            result["confidence"] = event.payload.get("confidence")
            result["needs_clarification"] = event.payload.get("needs_clarification")
        elif event.type == "feed":
            result["feed"] = event.payload
            result["round"] = event.payload.get("round")
            result["preference"] = event.payload.get("preference")
        elif event.type == "token":
            tokens.append(event.payload.get("content", ""))
        elif event.type == "error":
            result["error"] = event.payload
        elif event.type == "done":
            result["round"] = event.payload.get("round", result.get("round"))

    if tokens:
        result["content"] = "".join(tokens)
    return result


@router.post("/recommend")
async def recommend(request: RecommendRequest):
    if request.stream:
        return EventSourceResponse(
            event_generator(
                request.command,
                request.session_id,
                k=request.k,
            )
        )
    return await collect_round_result(
        request.command,
        request.session_id,
        k=request.k,
    )
