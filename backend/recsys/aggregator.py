"""Aggregator tool — combine, rank, and materialize the feed (paper §3.3.1).

Final score per candidate: ``total = matcher.combined + attenuator.penalty``
(penalty is <= 0). Candidates are ranked by ``total`` descending, with a
deterministic tie-break (nearer first, then POI id), truncated to top-K, and
mapped to :class:`ScoredPOIItem` with an *additive* :class:`ScoreBreakdown`
where ``matcher_semantic + matcher_collaborative + attenuator == total``.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.feed import RecommendationFeed, ScoreBreakdown, ScoredPOIItem
from domain.poi import POIItem
from domain.preference import PreferenceProfile
from domain.weather import WeatherSnapshot
from recsys.attenuator import AttenuatorScore
from recsys.config import DEFAULT_SCORING_CONFIG
from recsys.matcher import MatcherScores


@dataclass
class ScoredCandidate:
    """Intermediate scored candidate prior to feed materialization."""

    item: POIItem
    matcher: MatcherScores
    attenuator: AttenuatorScore
    total: float


def _rank_key(candidate: ScoredCandidate) -> tuple[float, float, str]:
    """Sort key: highest total first, then nearer, then stable by id."""
    distance = (
        candidate.item.distance_m
        if candidate.item.distance_m is not None
        else float("inf")
    )
    return (-candidate.total, distance, candidate.item.id)


def aggregate_and_rank(
    pois: list[POIItem],
    matcher_scores: dict[str, MatcherScores],
    attenuator_scores: dict[str, AttenuatorScore],
    *,
    k: int,
) -> list[ScoredPOIItem]:
    """Combine scores, rank, truncate to ``k``, and build ranked feed items."""
    candidates: list[ScoredCandidate] = []
    for poi in pois:
        matcher = matcher_scores.get(poi.id, MatcherScores())
        attenuator = attenuator_scores.get(poi.id, AttenuatorScore())
        total = matcher.combined + attenuator.penalty
        candidates.append(
            ScoredCandidate(
                item=poi,
                matcher=matcher,
                attenuator=attenuator,
                total=total,
            )
        )

    candidates.sort(key=_rank_key)

    scored_items: list[ScoredPOIItem] = []
    for rank, candidate in enumerate(candidates[:k], start=1):
        breakdown = ScoreBreakdown(
            filter_passed=True,
            matcher_semantic=candidate.matcher.semantic_contribution,
            matcher_collaborative=candidate.matcher.collaborative_contribution,
            attenuator=candidate.attenuator.penalty,
            total=candidate.total,
        )
        scored_items.append(
            ScoredPOIItem(
                item=candidate.item,
                rank=rank,
                score=candidate.total,
                breakdown=breakdown,
            )
        )
    return scored_items


def build_recommendation_feed(
    pois: list[POIItem],
    matcher_scores: dict[str, MatcherScores],
    attenuator_scores: dict[str, AttenuatorScore],
    *,
    preference: PreferenceProfile,
    round: int = 1,
    user_command: str | None = None,
    total_candidates: int | None = None,
    k: int = DEFAULT_SCORING_CONFIG.k,
    weather: WeatherSnapshot | None = None,
) -> RecommendationFeed:
    """Rank candidates and wrap them into a :class:`RecommendationFeed` R_t."""
    items = aggregate_and_rank(pois, matcher_scores, attenuator_scores, k=k)
    return RecommendationFeed(
        round=round,
        items=items,
        preference_snapshot=preference,
        user_command=user_command,
        total_candidates=(
            total_candidates if total_candidates is not None else len(pois)
        ),
        k=k,
        weather=weather,
    )
