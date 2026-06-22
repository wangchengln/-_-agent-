#!/usr/bin/env python3
"""Tests for recsys Matcher tool (Block E) — deterministic mock embeddings."""

from __future__ import annotations

from typing import Callable

from domain.poi import POIItem
from domain.preference import PreferenceProfile
from domain.types import GeoLocation
from recsys.config import ScoringConfig
from recsys.matcher import (
    _collaborative_score,
    _semantic_score,
    score_matcher,
)


def _poi(
    poi_id: str,
    *,
    description: str = "",
    rating: float | None = None,
    distance_m: float | None = None,
) -> POIItem:
    return POIItem(
        id=poi_id,
        name=poi_id,
        type="风景名胜",
        location=GeoLocation(lng=121.0, lat=31.0, city="上海"),
        rating=rating,
        distance_m=distance_m,
        description=description or poi_id,
    )


def _embed_from(mapping: dict[str, list[float]], dim: int = 3) -> Callable:
    def fn(texts: list[str]) -> list[list[float]]:
        return [mapping.get(text, [0.0] * dim) for text in texts]

    return fn


def _pref_with_tags(*tags: str) -> PreferenceProfile:
    pref = PreferenceProfile.empty()
    pref.positive_soft.tags = list(tags)
    return pref


# --- semantic / collaborative units ---

def test_semantic_score_clamps_negative() -> None:
    assert _semantic_score([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == 1.0
    assert _semantic_score([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]) == 0.0
    assert _semantic_score([1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]) == 0.0  # clamped
    print("semantic score clamp OK")


def test_collaborative_rating_default() -> None:
    config = ScoringConfig()
    # rating None -> default 3.0 -> 0.6; distance None -> 0.5
    poi = _poi("p")
    collab = _collaborative_score(poi, None, config)
    assert abs(collab - (0.6 * 0.6 + 0.4 * 0.5)) < 1e-9
    print("collaborative default OK")


def test_collaborative_distance_closer_is_higher() -> None:
    config = ScoringConfig()
    near = _poi("near", rating=4.0, distance_m=100.0)
    far = _poi("far", rating=4.0, distance_m=1000.0)
    near_score = _collaborative_score(near, 1000.0, config)
    far_score = _collaborative_score(far, 1000.0, config)
    assert near_score > far_score
    # near: 0.6*0.8 + 0.4*0.9 = 0.84 ; far: 0.6*0.8 + 0.4*0.0 = 0.48
    assert abs(near_score - 0.84) < 1e-9
    assert abs(far_score - 0.48) < 1e-9
    print("collaborative distance OK")


# --- score_matcher with semantic ---

def test_score_matcher_semantic_ranks_relevant_higher() -> None:
    pref = _pref_with_tags("文艺")
    config = ScoringConfig()
    poi_a = _poi("A", description="descA")
    poi_b = _poi("B", description="descB")
    embed_fn = _embed_from(
        {
            "文艺": [1.0, 0.0, 0.0],
            "descA": [1.0, 0.0, 0.0],  # aligned -> cos 1
            "descB": [0.0, 1.0, 0.0],  # orthogonal -> cos 0
        }
    )
    scores = score_matcher([poi_a, poi_b], pref, config, embed_fn=embed_fn)

    assert scores["A"].semantic == 1.0
    assert scores["B"].semantic == 0.0
    # both share the same collaborative (no rating/distance) = 0.56
    assert abs(scores["A"].collaborative - 0.56) < 1e-9
    # combined A = 0.65*1 + 0.35*0.56 ; B = 0.35*0.56
    assert abs(scores["A"].combined - (0.65 + 0.35 * 0.56)) < 1e-9
    assert abs(scores["B"].combined - (0.35 * 0.56)) < 1e-9
    assert scores["A"].combined > scores["B"].combined
    print("score_matcher semantic ranking OK")


# --- E5 degradation: empty query ---

def test_score_matcher_empty_query_skips_embedding() -> None:
    pref = PreferenceProfile.empty()  # no soft prefs -> empty query
    config = ScoringConfig()

    def boom(texts: list[str]) -> list[list[float]]:
        raise AssertionError("embed_fn must not be called when query is empty")

    poi = _poi("p", rating=4.0, distance_m=None)
    scores = score_matcher([poi], pref, config, embed_fn=boom)
    assert scores["p"].semantic == 0.0
    # pure collaborative fallback
    assert scores["p"].combined == scores["p"].collaborative
    print("score_matcher empty-query degrade OK")


def test_score_matcher_short_query_below_threshold() -> None:
    pref = _pref_with_tags("文艺")  # query "文艺" length 2
    config = ScoringConfig().model_copy(update={"min_semantic_query_len": 5})

    def boom(texts: list[str]) -> list[list[float]]:
        raise AssertionError("embed_fn must not be called below min query length")

    poi = _poi("p")
    scores = score_matcher([poi], pref, config, embed_fn=boom)
    assert scores["p"].semantic == 0.0
    print("score_matcher short-query threshold OK")


def test_score_matcher_empty_pool() -> None:
    assert score_matcher([], PreferenceProfile.empty()) == {}
    print("score_matcher empty pool OK")


def test_score_matcher_distance_normalization_pool_wide() -> None:
    pref = PreferenceProfile.empty()  # collaborative-only
    config = ScoringConfig()
    near = _poi("near", rating=4.0, distance_m=100.0)
    far = _poi("far", rating=4.0, distance_m=1000.0)
    scores = score_matcher([near, far], pref, config)
    assert scores["near"].combined > scores["far"].combined
    assert abs(scores["near"].combined - 0.84) < 1e-9
    assert abs(scores["far"].combined - 0.48) < 1e-9
    print("score_matcher pool-wide distance OK")


if __name__ == "__main__":
    test_semantic_score_clamps_negative()
    test_collaborative_rating_default()
    test_collaborative_distance_closer_is_higher()
    test_score_matcher_semantic_ranks_relevant_higher()
    test_score_matcher_empty_query_skips_embedding()
    test_score_matcher_short_query_below_threshold()
    test_score_matcher_empty_pool()
    test_score_matcher_distance_normalization_pool_wide()
    print("ALL TESTS PASSED")
