"""Planner Agent — façade over the deterministic ScoringPipeline.

The Planner consumes a structured preference ``P_{t+1}`` (from the Parser) and
produces the next recommendation feed ``R_{t+1}``. Unlike the Parser it does not
call an LLM: it orchestrates Amap recall + the deterministic scoring tool chain.

It also adds IRF-level error policy on top of the raw pipeline:
- a missing/unresolvable anchor -> :class:`AnchorNotResolvedError`
- a genuinely empty candidate pool -> :class:`EmptyCandidatePoolError`

Runs the synchronous pipeline in a worker thread so it is safe to ``await`` from
the async API layer.
"""

from __future__ import annotations

import asyncio
import logging

from pydantic import BaseModel, Field

from domain.feed import RecommendationFeed
from domain.irf_state import IRFSessionState
from domain.preference import PreferenceProfile
from recsys.candidate import AnchorResolutionError
from recsys.scoring import ScoringPipeline

logger = logging.getLogger(__name__)


class PlannerError(Exception):
    """Base error for Planner Agent failures."""


class AnchorNotResolvedError(PlannerError):
    """Raised when the search anchor cannot be resolved to coordinates."""


class EmptyCandidatePoolError(PlannerError):
    """Raised when no POIs can be retrieved near the anchor."""


class PlannerInput(BaseModel):
    """Input bundle for :meth:`PlannerAgent.plan`."""

    preference: PreferenceProfile = Field(
        description="Explicit preference P_{t+1} to plan against",
    )
    round: int = Field(default=1, ge=1, description="IRF round index for R_t")
    user_command: str | None = Field(
        default=None,
        description="Natural language command c_t that triggered this feed",
    )
    k: int | None = Field(
        default=None,
        ge=1,
        description="Top-K feed size; defaults to the pipeline config",
    )


class PlannerAgent:
    """Turns a preference into a recommendation feed via the scoring pipeline."""

    def __init__(self, pipeline: ScoringPipeline | None = None) -> None:
        self._pipeline = pipeline or ScoringPipeline()

    async def plan(self, planner_input: PlannerInput) -> RecommendationFeed:
        """Generate the feed for a preference, applying IRF error policy."""
        try:
            feed = await asyncio.to_thread(
                self._pipeline.run,
                planner_input.preference,
                round=planner_input.round,
                command=planner_input.user_command,
                k=planner_input.k,
            )
        except AnchorResolutionError as exc:
            raise AnchorNotResolvedError(str(exc)) from exc

        if feed.total_candidates == 0:
            raise EmptyCandidatePoolError(
                "no POIs found near the anchor; consider relaxing constraints"
            )

        logger.debug(
            "planner produced feed round=%d items=%d candidates=%s",
            feed.round,
            len(feed.items),
            feed.total_candidates,
        )
        return feed

    async def plan_for_session(
        self,
        state: IRFSessionState,
        command: str | None = None,
    ) -> RecommendationFeed:
        """Plan using the preference stored in an IRF session state."""
        planner_input = PlannerInput(
            preference=state.preference,
            round=state.round,
            user_command=command or state.preference.source_command,
        )
        return await self.plan(planner_input)


planner_agent = PlannerAgent()
