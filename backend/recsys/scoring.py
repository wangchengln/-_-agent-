"""ScoringPipeline — adaptive orchestration of the deterministic tool chain.

Implements the paper's §3.3.2 idea that the Planner activates only the stages a
given preference state needs:

  retrieve -> [Filter] -> Matcher (collaborative always, semantic if soft prefs)
           -> [Attenuator] -> Aggregator -> RecommendationFeed

- Filter runs only when a hard constraint exists (otherwise it's a no-op).
- Matcher always runs so the feed has a meaningful ranking; its semantic signal
  self-degrades when there is no positive soft-preference text.
- Attenuator runs only when there is negative intent (text or dislike tags).

The pipeline is synchronous (matching the sync AmapClient + embedding client).
``PlannerAgent`` wraps it in a thread for async API contexts.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from domain.feed import RecommendationFeed
from domain.preference import PreferenceProfile
from domain.types import VenueType
from recsys.aggregator import build_recommendation_feed
from recsys.attenuator import score_attenuator
from recsys.candidate import retrieve_candidates
from recsys.config import DEFAULT_SCORING_CONFIG, ScoringConfig
from recsys.embeddings import batch_embed_with_cache
from recsys.filter import apply_filter
from recsys.matcher import score_matcher
from recsys.types import EmbeddingVector

EmbedFn = Callable[[list[str]], list[EmbeddingVector]]

logger = logging.getLogger(__name__)


class ScoringPipeline:
    """Orchestrates candidate retrieval and the deterministic scoring stages."""

    def __init__(
        self,
        config: ScoringConfig = DEFAULT_SCORING_CONFIG,
        *,
        amap_client: Any | None = None,
        embed_fn: EmbedFn | None = None,
    ) -> None:
        self.config = config
        self._amap_client = amap_client
        self._embed_fn = embed_fn or batch_embed_with_cache

    def _needs_filter(self, preference: PreferenceProfile) -> bool:
        hard = preference.positive_hard
        negative = preference.negative_hard
        return any(
            [
                hard.radius_m is not None,
                bool(hard.categories),
                hard.max_price is not None,
                hard.min_rating is not None,
                hard.open_now is not None,
                hard.venue_type != VenueType.ANY,
                bool(negative.exclude_categories),
                bool(negative.exclude_poi_ids),
                bool(negative.exclude_tags),
            ]
        )

    def _needs_matcher(self, preference: PreferenceProfile) -> bool:
        """Whether semantic matching adds value (collaborative always runs)."""
        return bool(preference.positive_soft_query_text().strip())

    def _needs_attenuator(self, preference: PreferenceProfile) -> bool:
        return bool(preference.negative_semantic_query_text().strip()) or bool(
            preference.negative_soft.dislike_tags
        )

    def _empty_feed(
        self,
        preference: PreferenceProfile,
        *,
        round: int,
        command: str | None,
        total_candidates: int,
        k: int,
    ) -> RecommendationFeed:
        return build_recommendation_feed(
            [],
            {},
            {},
            preference=preference,
            round=round,
            user_command=command,
            total_candidates=total_candidates,
            k=k,
        )

    def run(
        self,
        preference: PreferenceProfile,
        *,
        round: int = 1,
        command: str | None = None,
        k: int | None = None,
    ) -> RecommendationFeed:
        """Run the full pipeline and return a ranked :class:`RecommendationFeed`."""
        k = k or self.config.k

        candidates = retrieve_candidates(
            preference, self.config, client=self._amap_client
        )
        total_candidates = len(candidates)
        if not candidates:
            logger.info("scoring: empty candidate pool")
            return self._empty_feed(
                preference,
                round=round,
                command=command,
                total_candidates=0,
                k=k,
            )

        if self._needs_filter(preference):
            result = apply_filter(candidates, preference)
            passed = result.passed
            logger.debug(
                "scoring filter: %d passed / %d rejected %s",
                result.passed_count,
                result.rejected_count,
                result.reason_counts(),
            )
        else:
            passed = candidates

        if not passed:
            logger.info("scoring: all %d candidates filtered out", total_candidates)
            return self._empty_feed(
                preference,
                round=round,
                command=command,
                total_candidates=total_candidates,
                k=k,
            )

        logger.debug(
            "scoring matcher: %s",
            "semantic+collaborative"
            if self._needs_matcher(preference)
            else "collaborative only",
        )
        matcher_scores = score_matcher(
            passed, preference, self.config, embed_fn=self._embed_fn
        )

        if self._needs_attenuator(preference):
            attenuator_scores = score_attenuator(
                passed, preference, self.config, embed_fn=self._embed_fn
            )
        else:
            attenuator_scores = {}

        return build_recommendation_feed(
            passed,
            matcher_scores,
            attenuator_scores,
            preference=preference,
            round=round,
            user_command=command,
            total_candidates=total_candidates,
            k=k,
        )
