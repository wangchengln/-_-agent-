"""Scoring pipeline configuration — single source of tuning constants.

Centralizes every weight, threshold, and default used by the deterministic
IRF scoring stages (Filter / Matcher / Attenuator / Aggregator) so that no
individual stage hardcodes magic numbers.

Mapping to the RecBot paper:
  - ``alpha_semantic`` / ``alpha_collaborative``: Matcher dual-signal weights.
    Semantic = embedding similarity to positive soft preferences; collaborative
    = a cheap rating/distance surrogate for the paper's AIA sequence model.
  - ``beta_attenuator``: Attenuator penalty coefficient β for negative intent.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

_WEIGHT_SUM_TOLERANCE = 1e-6


class ScoringConfig(BaseModel):
    """Immutable tuning parameters for the scoring pipeline.

    Frozen so a shared instance can be passed safely across stages. Use
    :meth:`pydantic.BaseModel.model_copy` (``update={...}``) to derive variants
    in tests instead of mutating in place.
    """

    model_config = ConfigDict(frozen=True)

    # --- Output / candidate pool sizing ---
    k: int = Field(default=5, ge=1, description="Top-K feed size R_t")
    default_radius_m: int = Field(
        default=5000,
        ge=0,
        description="Search radius when no hard-constraint radius is set",
    )
    max_candidates: int = Field(
        default=80,
        ge=1,
        description="Candidate pool cap before scoring (controls embedding cost)",
    )

    # --- Matcher weights (must sum to 1.0) ---
    alpha_semantic: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Matcher semantic similarity weight α",
    )
    alpha_collaborative: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Matcher collaborative (rating/distance) weight",
    )

    # --- Collaborative surrogate sub-weights (must sum to 1.0) ---
    collab_rating_weight: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Rating share inside the collaborative surrogate score",
    )
    collab_distance_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Distance share inside the collaborative surrogate score",
    )
    default_rating: float = Field(
        default=3.0,
        ge=0.0,
        le=5.0,
        description="Fallback rating for POIs missing a rating value",
    )

    # --- Attenuator weights ---
    beta_attenuator: float = Field(
        default=0.4,
        ge=0.0,
        description="Negative-intent semantic penalty coefficient β",
    )
    dislike_tag_penalty: float = Field(
        default=0.1,
        ge=0.0,
        description="Extra penalty per POI tag matching a dislike tag",
    )

    # --- Thresholds ---
    min_semantic_query_len: int = Field(
        default=2,
        ge=0,
        description="Skip embedding when query text is shorter than this",
    )

    @model_validator(mode="after")
    def _validate_weight_sums(self) -> Self:
        matcher_sum = self.alpha_semantic + self.alpha_collaborative
        if abs(matcher_sum - 1.0) > _WEIGHT_SUM_TOLERANCE:
            raise ValueError(
                "alpha_semantic + alpha_collaborative must equal 1.0 "
                f"(got {matcher_sum:.4f})"
            )

        collab_sum = self.collab_rating_weight + self.collab_distance_weight
        if abs(collab_sum - 1.0) > _WEIGHT_SUM_TOLERANCE:
            raise ValueError(
                "collab_rating_weight + collab_distance_weight must equal 1.0 "
                f"(got {collab_sum:.4f})"
            )
        return self


DEFAULT_SCORING_CONFIG = ScoringConfig()
"""Process-wide default config; import this instead of constructing per call."""
