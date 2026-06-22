"""Recommendation scoring package — Planner Agent deterministic tool chain.

Implements the IRF scoring pipeline mapped from the RecBot paper:
``retrieve -> Filter -> Matcher -> Attenuator -> Aggregator -> R_t``.

Block A provides the shared configuration (:class:`ScoringConfig`) and type
aliases consumed by every downstream stage. Later blocks add the stage modules
(``candidate``, ``filter``, ``matcher``, ``attenuator``, ``aggregator``,
``scoring``) and export them here.
"""

from recsys.candidate import (
    AnchorResolutionError,
    CandidateError,
    resolve_anchor,
    retrieve_candidates,
)
from recsys.config import DEFAULT_SCORING_CONFIG, ScoringConfig
from recsys.aggregator import (
    ScoredCandidate,
    aggregate_and_rank,
    build_recommendation_feed,
)
from recsys.attenuator import AttenuatorScore, score_attenuator
from recsys.filter import FilterResult, RejectedCandidate, apply_filter
from recsys.matcher import MatcherScores, score_matcher
from recsys.scoring import ScoringPipeline
from recsys.embeddings import (
    batch_embed_with_cache,
    cosine_similarity,
    embed_text,
    embed_texts,
    get_embedder,
    reset_embedding_cache,
    set_embedder,
)
from recsys.types import CandidatePool, EmbeddingVector

__all__ = [
    "ScoringConfig",
    "DEFAULT_SCORING_CONFIG",
    "CandidatePool",
    "EmbeddingVector",
    "get_embedder",
    "set_embedder",
    "reset_embedding_cache",
    "embed_texts",
    "embed_text",
    "batch_embed_with_cache",
    "cosine_similarity",
    "retrieve_candidates",
    "resolve_anchor",
    "CandidateError",
    "AnchorResolutionError",
    "apply_filter",
    "FilterResult",
    "RejectedCandidate",
    "score_matcher",
    "MatcherScores",
    "score_attenuator",
    "AttenuatorScore",
    "aggregate_and_rank",
    "build_recommendation_feed",
    "ScoredCandidate",
    "ScoringPipeline",
]
