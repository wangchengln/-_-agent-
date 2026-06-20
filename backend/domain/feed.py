"""Recommendation feed model (IRF state R_t)."""

from __future__ import annotations

import time
from typing import Self

from pydantic import BaseModel, Field, model_validator

from domain.poi import POIItem
from domain.preference import PreferenceProfile


class ScoreBreakdown(BaseModel):
    """Per-component score contributions for explainability."""

    filter_passed: bool = True
    matcher_semantic: float | None = Field(
        default=None,
        description="Semantic similarity component",
    )
    matcher_collaborative: float | None = Field(
        default=None,
        description="Collaborative / popularity component",
    )
    attenuator: float | None = Field(
        default=None,
        description="Negative preference penalty (typically <= 0)",
    )
    total: float | None = Field(default=None, description="Final aggregated score")


class ScoredPOIItem(BaseModel):
    """POI candidate with ranking metadata."""

    item: POIItem
    rank: int | None = Field(default=None, ge=1)
    score: float | None = Field(default=None, description="Final ranking score")
    breakdown: ScoreBreakdown | None = None

    @property
    def poi_id(self) -> str:
        return self.item.id


class RecommendationFeed(BaseModel):
    """Top-K recommendation feed shown to the user in one IRF round."""

    round: int = Field(default=1, ge=1, description="IRF interaction round index")
    items: list[ScoredPOIItem] = Field(default_factory=list)
    preference_snapshot: PreferenceProfile = Field(
        default_factory=PreferenceProfile.empty,
        description="Preference state P_t when this feed was generated",
    )
    generated_at: float = Field(
        default_factory=time.time,
        description="Unix timestamp",
    )
    user_command: str | None = Field(
        default=None,
        description="Natural language command c_t for this round",
    )
    total_candidates: int | None = Field(
        default=None,
        ge=0,
        description="Candidate pool size before top-K truncation",
    )
    k: int = Field(default=5, ge=1, description="Requested top-K size")

    @model_validator(mode="after")
    def validate_ranking(self) -> Self:
        if not self.items:
            return self

        ranks = [item.rank for item in self.items if item.rank is not None]
        if ranks and len(ranks) != len(self.items):
            raise ValueError("either all feed items must have rank or none should")

        if ranks:
            expected = list(range(1, len(self.items) + 1))
            if sorted(ranks) != expected:
                raise ValueError("ranks must be contiguous starting from 1")
        else:
            for index, scored_item in enumerate(self.items, start=1):
                scored_item.rank = index
        return self

    @property
    def poi_ids(self) -> list[str]:
        return [item.poi_id for item in self.items]

    @property
    def scores(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for scored_item in self.items:
            if scored_item.score is not None:
                result[scored_item.poi_id] = scored_item.score
        return result

    @classmethod
    def from_poi_items(
        cls,
        poi_items: list[POIItem],
        *,
        round: int = 1,
        preference_snapshot: PreferenceProfile | None = None,
        user_command: str | None = None,
        total_candidates: int | None = None,
        k: int = 5,
    ) -> Self:
        """Build an unranked feed placeholder before Aggregator scoring."""
        snapshot = preference_snapshot or PreferenceProfile.empty()
        scored_items = [
            ScoredPOIItem(item=item, rank=index, score=None)
            for index, item in enumerate(poi_items[:k], start=1)
        ]
        return cls(
            round=round,
            items=scored_items,
            preference_snapshot=snapshot,
            user_command=user_command,
            total_candidates=total_candidates or len(poi_items),
            k=k,
        )
