"""IRF interaction loop — wires Parser Agent and Planner Agent into one round.

Implements one transition of the paper's state machine
``S_t = {R_t, c_t, P_t, H_t}``:

    c_t (user command)
      -> ParserAgent.parse        => P_{t+1}
      -> apply_parser_output       => round++, history += c_t, preference = P_{t+1}
      -> PlannerAgent.plan         => R_{t+1} (deterministic scoring pipeline)
      -> commit_irf_round            => single write of P + R + round + H

The loop is *transport agnostic*: :meth:`IRFLoop.run_round` is an async
generator that yields typed :class:`LoopEvent` objects. The SSE endpoint
(``api/recommend.py``) is responsible for turning those into wire events, so
the business logic here stays unit-testable without HTTP.

Design decisions (Day 4):
- The feed is labeled with the *pre-increment* round, so the first feed is
  round 1 while the persisted state advances to the next round.
- State is persisted only on a fully successful round. If the Planner raises
  (missing anchor / empty pool), nothing is written and the round number is
  preserved so the user can refine the command and retry.
- Recommendation reasons are built deterministically from the score breakdown
  (option B): zero extra latency / tokens. An LLM-written critique can replace
  this in the Day 5 experience pass.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Iterator, Literal

from pydantic import BaseModel, Field

from domain.feed import RecommendationFeed, ScoredPOIItem
from domain.irf_state import IRFSessionState
from domain.preference import PreferenceProfile
from graph.parser_agent import ParserAgent, ParserAgentError, parser_agent
from graph.planner_agent import (
    AnchorNotResolvedError,
    EmptyCandidatePoolError,
    PlannerAgent,
    PlannerInput,
    planner_agent,
)
from graph.session_manager import SessionManager, session_manager
from recsys.errors import (
    LOW_CONFIDENCE_HINT,
    error_message,
    normalize_command,
)

logger = logging.getLogger(__name__)

LoopEventType = Literal["intent", "stage", "feed", "token", "error", "done"]


class LoopEvent(BaseModel):
    """Transport-agnostic event emitted during one IRF round.

    ``type`` mirrors the SSE event name the API layer will use; ``payload`` is
    a JSON-serializable dict ready to be ``json.dumps``'d downstream.
    """

    type: LoopEventType = Field(description="Event kind / SSE event name")
    payload: dict[str, Any] = Field(default_factory=dict)


def intent_event(
    intent_summary: str,
    confidence: str,
    *,
    needs_clarification: bool = False,
) -> LoopEvent:
    """Parser result: what the loop understood from the command."""
    return LoopEvent(
        type="intent",
        payload={
            "intent_summary": intent_summary,
            "confidence": confidence,
            "needs_clarification": needs_clarification,
        },
    )


def stage_event(name: str, status: Literal["start", "end"]) -> LoopEvent:
    """Scoring-pipeline stage marker (drives the front-end ThoughtChain)."""
    return LoopEvent(type="stage", payload={"name": name, "status": status})


def token_event(content: str) -> LoopEvent:
    """A chunk of the natural-language recommendation rationale."""
    return LoopEvent(type="token", payload={"content": content})


def error_event(
    code: str,
    message: str | None = None,
    *,
    session_id: str | None = None,
    round_index: int | None = None,
    retry_hint: str | None = None,
) -> LoopEvent:
    """Recoverable error with a stable ``code`` for front-end handling."""
    from recsys.errors import RETRY_HINTS

    payload: dict[str, Any] = {
        "code": code,
        "message": message or error_message(code),
        "retry_hint": retry_hint or RETRY_HINTS.get(code),
    }
    if session_id is not None:
        payload["session_id"] = session_id
    if round_index is not None:
        payload["round"] = round_index
    return LoopEvent(type="error", payload=payload)


def done_event(session_id: str, round_index: int) -> LoopEvent:
    """Round finished successfully."""
    return LoopEvent(
        type="done",
        payload={"session_id": session_id, "round": round_index},
    )


def _format_distance(distance_m: float | None) -> str | None:
    if distance_m is None:
        return None
    if distance_m >= 1000:
        return f"{distance_m / 1000:.1f}km"
    return f"{int(distance_m)}m"


def feed_item_payload(scored: ScoredPOIItem, preference: PreferenceProfile) -> dict[str, Any]:
    """Slim, front-end-friendly view of one feed card.

    Deliberately omits internal scoring internals (raw Amap payload, full
    breakdown) and instead surfaces only what a card needs to render, plus a
    human-readable ``reason``. Includes ``lng``/``lat`` (GCJ-02) for map and
    itinerary planning (Day 6).
    """
    poi = scored.item
    return {
        "rank": scored.rank,
        "poi_id": poi.id,
        "name": poi.name,
        "type": poi.type,
        "lng": poi.location.lng,
        "lat": poi.location.lat,
        "rating": poi.rating,
        "distance_m": poi.distance_m,
        "cost": poi.cost,
        "address": poi.address,
        "tags": poi.tags,
        "photos": poi.photos,
        "score": scored.score,
        "reason": _build_item_reason(scored, preference),
    }


def _build_item_reason(scored: ScoredPOIItem, preference: PreferenceProfile) -> str:
    """Deterministic explanation derived from the score breakdown (option B)."""
    poi = scored.item
    bits: list[str] = []

    distance = _format_distance(poi.distance_m)
    if distance is not None:
        bits.append(f"距锚点约{distance}")
    if poi.rating is not None:
        bits.append(f"评分{poi.rating:g}")

    breakdown = scored.breakdown
    if breakdown is not None:
        if breakdown.matcher_semantic is not None and breakdown.matcher_semantic > 0:
            vibe = preference.positive_soft.tags or preference.positive_soft.keywords
            if vibe:
                bits.append("契合你偏好的「" + "、".join(vibe[:3]) + "」氛围")
            else:
                bits.append("语义匹配度较高")
        if breakdown.attenuator is not None and breakdown.attenuator < 0:
            bits.append("（含轻微负向扣分）")

    if not bits:
        return f"{poi.name}。"
    return f"{poi.name}：" + "，".join(bits) + "。"


def feed_event(
    feed: RecommendationFeed,
    preference: PreferenceProfile,
) -> LoopEvent:
    """The recommendation feed R_{t+1}: items + user preference + weather context.

    ``preference`` is the persisted Parser profile (sidebar). Item ``reason`` text
    uses ``feed.preference_snapshot`` (may include ephemeral weather adjustments).
    """
    scoring_pref = feed.preference_snapshot
    weather_payload = (
        feed.weather.model_dump(mode="json") if feed.weather is not None else None
    )
    return LoopEvent(
        type="feed",
        payload={
            "round": feed.round,
            "k": feed.k,
            "total_candidates": feed.total_candidates,
            "items": [
                feed_item_payload(item, scoring_pref) for item in feed.items
            ],
            "preference": preference.model_dump(mode="json"),
            "preference_summary": preference.to_parser_context(),
            "weather": weather_payload,
        },
    )


def _iter_reason_tokens(feed: RecommendationFeed) -> Iterator[str]:
    """Stream the rationale as small chunks (intro + one line per card)."""
    yield f"为你找到 {len(feed.items)} 个去处（第{feed.round}轮）：\n"
    for scored in feed.items:
        reason = _build_item_reason(scored, feed.preference_snapshot)
        yield f"{scored.rank}. {reason}\n"


class IRFLoop:
    """One-round orchestrator for Parser -> Planner over a session's IRF state."""

    def __init__(
        self,
        *,
        parser: ParserAgent | None = None,
        planner: PlannerAgent | None = None,
        sessions: SessionManager | None = None,
    ) -> None:
        self._parser = parser or parser_agent
        self._planner = planner or planner_agent
        self._sessions = sessions or session_manager

    async def run_round(
        self,
        session_id: str,
        command: str,
        *,
        k: int | None = None,
    ) -> AsyncIterator[LoopEvent]:
        """Run one IRF round and stream typed events.

        Persists ``P_{t+1}`` + ``R_{t+1}`` only when the round fully succeeds.
        """
        state = self._sessions.get_irf_state(session_id)

        normalized, invalid_code = normalize_command(command)
        if invalid_code is not None:
            yield error_event(
                invalid_code,
                session_id=session_id,
                round_index=state.round,
            )
            return
        command = normalized

        # 1. Parse the command into a complete next preference P_{t+1}.
        try:
            parser_input = state.build_parser_input(command)
            parser_output = await self._parser.parse(parser_input)
        except ParserAgentError as exc:
            logger.warning("parser failed for command %r: %s", command, exc)
            yield error_event(
                "parse_failed",
                session_id=session_id,
                round_index=state.round,
            )
            return
        except ValueError as exc:
            logger.warning("invalid parser input for command %r: %s", command, exc)
            yield error_event(
                "invalid_command",
                session_id=session_id,
                round_index=state.round,
            )
            return
        except Exception as exc:  # noqa: BLE001 — surface unexpected errors as events
            logger.exception("unexpected parser error")
            yield error_event(
                "internal_error",
                error_message("internal_error", detail=str(exc)),
                session_id=session_id,
                round_index=state.round,
            )
            return

        low_confidence = parser_output.confidence == "low"
        yield intent_event(
            parser_output.intent_summary,
            parser_output.confidence,
            needs_clarification=low_confidence,
        )
        if low_confidence:
            logger.warning(
                "parser low confidence for session %s command %r",
                session_id,
                command,
            )
            yield token_event(LOW_CONFIDENCE_HINT + "\n")

        # 2. Advance state in memory for Planner (round++, P_{t+1}, history).
        #    Feed is labeled with the pre-increment round so the first feed is 1.
        current_round = state.round
        next_state = state.apply_parser_output(command, parser_output)

        # 3. Plan the next feed R_{t+1} via the deterministic scoring pipeline.
        yield stage_event("planner", "start")
        try:
            feed = await self._planner.plan(
                PlannerInput(
                    preference=next_state.preference,
                    round=current_round,
                    user_command=command,
                    k=k,
                )
            )
        except AnchorNotResolvedError:
            logger.info("anchor unresolved for session %s", session_id)
            yield stage_event("planner", "end")
            yield error_event(
                "anchor_missing",
                session_id=session_id,
                round_index=state.round,
            )
            return
        except EmptyCandidatePoolError:
            logger.info("empty candidate pool for session %s", session_id)
            yield stage_event("planner", "end")
            yield error_event(
                "empty_pool",
                session_id=session_id,
                round_index=state.round,
            )
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("unexpected planner error")
            yield stage_event("planner", "end")
            yield error_event(
                "internal_error",
                error_message("internal_error", detail=str(exc)),
                session_id=session_id,
                round_index=state.round,
            )
            return
        yield stage_event("planner", "end")

        # 4. Commit the successful round (single write of P + R + round + H).
        final_state = self._sessions.commit_irf_round(
            session_id,
            state,
            command,
            parser_output,
            feed,
        )

        # 5. Emit the feed and stream its rationale.
        yield feed_event(feed, final_state.preference)
        for chunk in _iter_reason_tokens(feed):
            yield token_event(chunk)

        yield done_event(session_id, feed.round)


irf_loop = IRFLoop()


async def run_round(
    session_id: str,
    command: str,
    *,
    k: int | None = None,
) -> AsyncIterator[LoopEvent]:
    """Module-level convenience wrapper over the default :data:`irf_loop`."""
    async for event in irf_loop.run_round(session_id, command, k=k):
        yield event
