"""Attenuator tool — negative-preference penalty (paper §3.3.1).

Soft negatives don't remove items (that's the Filter's job for hard negatives);
instead they *reduce* a candidate's score so it can still appear, just ranked
lower. Two penalty signals, both ``<= 0``:

- **Semantic penalty**: ``-β * max(0, cosine(poi_emb, negative_intent_emb))`` —
  how much the POI resembles what the user said they dislike.
- **Tag penalty**: ``-dislike_tag_penalty * overlap`` — count of the POI's tags
  that appear in ``negative_soft.dislike_tags`` (an exact, cheap signal that
  complements the fuzzy semantic one).

When there is neither negative intent text nor dislike tags, every penalty is 0
and no embedding calls are made (F4 short-circuit).
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


class AttenuatorScore(BaseModel):
    """Per-POI negative penalty (all components ``<= 0``)."""

    semantic_penalty: float = 0.0
    tag_penalty: float = 0.0
    penalty: float = 0.0


def _semantic_penalty(
    poi_vector: EmbeddingVector,
    negative_vector: EmbeddingVector,
    beta: float,
) -> float:
    similarity = max(0.0, cosine_similarity(poi_vector, negative_vector))
    return -beta * similarity


def _tag_penalty(
    poi: POIItem,
    dislike_tags: list[str],
    per_tag_penalty: float,
) -> float:
    tagset = {tag.strip() for tag in poi.tags if tag.strip()}
    overlap = sum(1 for tag in dislike_tags if tag in tagset)
    return -per_tag_penalty * overlap


def score_attenuator(
    pois: list[POIItem],
    preference: PreferenceProfile,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
    *,
    embed_fn: EmbedFn | None = None,
) -> dict[str, AttenuatorScore]:
    """Score negative penalties, returning ``{poi_id: AttenuatorScore}``."""
    if not pois:
        return {}

    embed_fn = embed_fn or batch_embed_with_cache

    negative_text = preference.negative_semantic_query_text().strip()
    dislike_tags = [
        tag.strip() for tag in preference.negative_soft.dislike_tags if tag.strip()
    ]
    use_semantic = len(negative_text) >= config.min_semantic_query_len
    has_tags = bool(dislike_tags)

    if not use_semantic and not has_tags:
        return {poi.id: AttenuatorScore() for poi in pois}

    poi_vectors: dict[str, EmbeddingVector] = {}
    negative_vector: EmbeddingVector = []
    if use_semantic:
        descriptions = [poi.description for poi in pois]
        vectors = embed_fn(descriptions)
        for poi, vector in zip(pois, vectors):
            poi_vectors[poi.id] = vector
        negative_vector = embed_fn([negative_text])[0]

    scores: dict[str, AttenuatorScore] = {}
    for poi in pois:
        semantic_penalty = (
            _semantic_penalty(
                poi_vectors.get(poi.id, []),
                negative_vector,
                config.beta_attenuator,
            )
            if use_semantic
            else 0.0
        )
        tag_penalty = (
            _tag_penalty(poi, dislike_tags, config.dislike_tag_penalty)
            if has_tags
            else 0.0
        )
        scores[poi.id] = AttenuatorScore(
            semantic_penalty=semantic_penalty,
            tag_penalty=tag_penalty,
            penalty=semantic_penalty + tag_penalty,
        )

    return scores
