"""Matcher tool — positive scoring (paper §3.3.1).

Two complementary signals:
- **Semantic**: cosine similarity between a POI's description embedding and the
  embedding of the user's positive soft preferences.
- **Collaborative**: a cheap surrogate for the paper's AIA sequence model, built
  from Amap rating + distance (we have no user behaviour logs on Day 3).

``combined`` blends the two with the weights from :class:`ScoringConfig`.

Degradation (E5): when there is no usable positive soft preference text, the
semantic signal is skipped entirely (no embedding calls) and ``combined`` falls
back to the pure collaborative score, so the feed still ranks by popularity /
proximity.
"""

from __future__ import annotations

from typing import Callable

from pydantic import BaseModel

from domain.poi import POIItem
from domain.preference import PreferenceProfile
from recsys.config import DEFAULT_SCORING_CONFIG, ScoringConfig
from recsys.embeddings import batch_embed_with_cache, cosine_similarity
from recsys.types import EmbeddingVector

EmbedFn = Callable[[list[str]], list[EmbeddingVector]]


class MatcherScores(BaseModel):
    """Per-POI positive scores produced by the Matcher."""

    semantic: float = 0.0
    collaborative: float = 0.0
    semantic_contribution: float = 0.0
    collaborative_contribution: float = 0.0
    combined: float = 0.0


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _semantic_score(
    poi_vector: EmbeddingVector,
    query_vector: EmbeddingVector,
) -> float:
    """Positive semantic match strength in ``[0, 1]`` (negatives clamped to 0)."""
    return max(0.0, cosine_similarity(poi_vector, query_vector))


def _collaborative_score(
    poi: POIItem,
    max_distance: float | None,
    config: ScoringConfig,
) -> float:
    """Rating/distance surrogate for collaborative signal, in ``[0, 1]``.

    ``max_distance`` is the largest distance in the pool (precomputed once for
    efficiency). Missing rating uses ``config.default_rating``; missing distance
    is treated as neutral (0.5).
    """
    rating = poi.rating if poi.rating is not None else config.default_rating
    rating_norm = _clamp01(rating / 5.0)

    if poi.distance_m is None or max_distance is None:
        distance_norm = 0.5
    elif max_distance <= 0:
        distance_norm = 1.0
    else:
        distance_norm = _clamp01(1.0 - poi.distance_m / max_distance)

    return (
        config.collab_rating_weight * rating_norm
        + config.collab_distance_weight * distance_norm
    )


def score_matcher(
    pois: list[POIItem],
    preference: PreferenceProfile,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
    *,
    embed_fn: EmbedFn | None = None,
) -> dict[str, MatcherScores]:
    """Score a list of POIs, returning ``{poi_id: MatcherScores}``.

    POI description embeddings are batched (and cached) via ``embed_fn``
    (defaults to :func:`recsys.embeddings.batch_embed_with_cache`). Tests inject
    a deterministic ``embed_fn`` to avoid any network access.
    """
    if not pois:
        return {}

    embed_fn = embed_fn or batch_embed_with_cache

    query_text = preference.positive_soft_query_text().strip()
    use_semantic = len(query_text) >= config.min_semantic_query_len

    poi_vectors: dict[str, EmbeddingVector] = {}
    query_vector: EmbeddingVector = []
    if use_semantic:
        descriptions = [poi.description for poi in pois]
        vectors = embed_fn(descriptions)
        for poi, vector in zip(pois, vectors):
            poi_vectors[poi.id] = vector
        query_vector = embed_fn([query_text])[0]

    distances = [poi.distance_m for poi in pois if poi.distance_m is not None]
    max_distance = max(distances) if distances else None

    scores: dict[str, MatcherScores] = {}
    for poi in pois:
        collaborative = _collaborative_score(poi, max_distance, config)
        if use_semantic:
            semantic = _semantic_score(poi_vectors.get(poi.id, []), query_vector)
            semantic_contribution = config.alpha_semantic * semantic
            collaborative_contribution = config.alpha_collaborative * collaborative
            combined = semantic_contribution + collaborative_contribution
        else:
            # Pure-collaborative fallback: the collaborative score is taken at
            # full weight so the feed still ranks meaningfully (E5).
            semantic = 0.0
            semantic_contribution = 0.0
            collaborative_contribution = collaborative
            combined = collaborative

        scores[poi.id] = MatcherScores(
            semantic=semantic,
            collaborative=collaborative,
            semantic_contribution=semantic_contribution,
            collaborative_contribution=collaborative_contribution,
            combined=combined,
        )

    return scores
