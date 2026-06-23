"""IRF session state and Parser Agent I/O contracts.

Maps paper state S_t = {R_t, c_t, P_t, H_t} to typed models used at the
Parser Agent boundary.  Parser outputs a *complete* P_{t+1} (not a delta):
conflict resolution happens inside the LLM before serialization.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator

from domain.feed import RecommendationFeed
from domain.itinerary import WeekendItinerary
from domain.preference import PreferenceProfile

MAX_COMMAND_HISTORY = 5


class ParserInput(BaseModel):
    """Single-turn input bundle for ParserAgent.parse()."""

    command: str = Field(description="Natural language command c_t")
    round: int = Field(default=1, ge=1, description="Current IRF round index")
    preference: PreferenceProfile = Field(
        default_factory=PreferenceProfile.empty,
        description="Current explicit preference P_t",
    )
    feed: RecommendationFeed | None = Field(
        default=None,
        description="Current recommendation feed R_t (None on cold start)",
    )
    command_history: list[str] = Field(
        default_factory=list,
        description="Recent user commands (oldest first, capped externally)",
    )

    @field_validator("command")
    @classmethod
    def strip_command(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("command must not be empty")
        return stripped

    @classmethod
    def from_irf_state(
        cls,
        state: IRFSessionState,
        command: str,
    ) -> Self:
        """Build parser input from persisted session state + new command."""
        return cls(
            command=command,
            round=state.round,
            preference=state.preference,
            feed=state.current_feed,
            command_history=list(state.command_history),
        )

    def preference_context(self) -> str:
        """Compact P_t text for LLM prompt injection."""
        return self.preference.to_parser_context()

    def feed_context(self, *, max_items: int = 5) -> str:
        """Compact R_t text for LLM prompt injection."""
        if self.feed is None:
            return "(尚无推荐结果)"
        return self.feed.to_parser_context(max_items=max_items)

    def history_context(self) -> str:
        """Recent commands as a single prompt block."""
        if not self.command_history:
            return "(无历史命令)"
        lines = [f"- {cmd}" for cmd in self.command_history]
        return "\n".join(lines)


class ParserOutput(BaseModel):
    """Structured output from Parser Agent (complete P_{t+1})."""

    preference: PreferenceProfile = Field(
        description="Full updated preference profile P_{t+1}",
    )
    intent_summary: str = Field(
        description="One-sentence Chinese summary of what changed",
    )
    confidence: Literal["high", "low"] = Field(
        default="high",
        description="Parser confidence; low => UI may ask for clarification",
    )

    @field_validator("intent_summary")
    @classmethod
    def validate_intent_summary(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("intent_summary must not be empty")
        return stripped


class IRFSessionState(BaseModel):
    """Persisted IRF machine state for a chat session (stored under session.irf)."""

    round: int = Field(default=1, ge=1, description="Next feed generation round")
    preference: PreferenceProfile = Field(
        default_factory=PreferenceProfile.empty,
        description="Current explicit preference P_t",
    )
    current_feed: RecommendationFeed | None = Field(
        default=None,
        description="Latest recommendation feed R_t",
    )
    command_history: list[str] = Field(
        default_factory=list,
        description="Recent user commands, oldest first",
    )
    current_itinerary: WeekendItinerary | None = Field(
        default=None,
        description="Latest generated weekend itinerary (Day 6.3)",
    )

    @classmethod
    def empty(cls) -> Self:
        """Default state for a new IRF session."""
        return cls()

    @classmethod
    def from_session_dict(cls, data: dict | None) -> Self:
        """Parse IRF block from session JSON; tolerate missing/legacy data."""
        if not data:
            return cls.empty()
        return cls.model_validate(data)

    def to_session_dict(self) -> dict:
        """Serialize for session JSON persistence."""
        return self.model_dump(mode="json")

    def build_parser_input(self, command: str) -> ParserInput:
        """Create ParserInput from current state and a new user command."""
        return ParserInput.from_irf_state(self, command)

    def apply_parser_output(
        self,
        command: str,
        output: ParserOutput,
    ) -> Self:
        """Pure state transition after Parser succeeds.

        Updates P_t -> P_{t+1}, increments round, appends command history.
        Does *not* update current_feed (Planner responsibility in Day 3).
        """
        history = (self.command_history + [command.strip()])[-MAX_COMMAND_HISTORY:]
        return self.model_copy(
            update={
                "round": self.round + 1,
                "preference": output.preference,
                "command_history": history,
            }
        )

    def with_feed(self, feed: RecommendationFeed) -> Self:
        """Attach a newly generated feed R_{t+1} without changing preference."""
        return self.model_copy(update={"current_feed": feed})

    def with_itinerary(self, itinerary: WeekendItinerary) -> Self:
        """Attach a generated weekend itinerary without changing feed/preference."""
        return self.model_copy(update={"current_itinerary": itinerary})
