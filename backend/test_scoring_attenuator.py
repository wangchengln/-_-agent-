#!/usr/bin/env python3
"""Tests for recsys Attenuator tool (Block F) — deterministic mock embeddings."""

from __future__ import annotations

from typing import Callable

from domain.poi import POIItem
from domain.preference import PreferenceProfile
from domain.types import GeoLocation
from recsys.attenuator import score_attenuator
from recsys.config import ScoringConfig


def _poi(
    poi_id: str,
    *,
    description: str = "",
    tags: list[str] | None = None,
) -> POIItem:
    return POIItem(
        id=poi_id,
        name=poi_id,
        type="风景名胜",
        location=GeoLocation(lng=121.0, lat=31.0, city="上海"),
        tags=tags or [],
        description=description or poi_id,
    )


def _embed_from(mapping: dict[str, list[float]], dim: int = 3) -> Callable:
    def fn(texts: list[str]) -> list[list[float]]:
        return [mapping.get(text, [0.0] * dim) for text in texts]

    return fn


def _zeros_embed(dim: int = 3) -> Callable:
    def fn(texts: list[str]) -> list[list[float]]:
        return [[0.0] * dim for _ in texts]

    return fn


def test_no_negative_returns_zero_without_embedding() -> None:
    pref = PreferenceProfile.empty()

    def boom(texts: list[str]) -> list[list[float]]:
        raise AssertionError("embed_fn must not be called with no negatives")

    scores = score_attenuator([_poi("a"), _poi("b")], pref, embed_fn=boom)
    assert scores["a"].penalty == 0.0
    assert scores["b"].penalty == 0.0
    print("no-negative zero OK")


def test_tag_penalty_counts_overlap() -> None:
    pref = PreferenceProfile.empty()
    pref.negative_soft.dislike_tags = ["人多", "网红"]
    config = ScoringConfig()
    poi = _poi("p", tags=["人多", "网红", "文艺"])
    # zero embeddings isolate the tag penalty (semantic = 0)
    scores = score_attenuator([poi], pref, config, embed_fn=_zeros_embed())
    assert abs(scores["p"].tag_penalty - (-0.2)) < 1e-9
    assert scores["p"].semantic_penalty == 0.0
    assert abs(scores["p"].penalty - (-0.2)) < 1e-9
    print("tag penalty overlap OK")


def test_semantic_penalty_negative_for_disliked() -> None:
    pref = PreferenceProfile.empty()
    pref.negative_soft.dislike_keywords = ["太吵"]  # no dislike_tags -> tag penalty 0
    config = ScoringConfig()
    embed_fn = _embed_from(
        {
            "太吵": [1.0, 0.0, 0.0],
            "noisy": [1.0, 0.0, 0.0],  # cos 1 -> full penalty
            "quiet": [0.0, 1.0, 0.0],  # cos 0 -> no penalty
        }
    )
    noisy = _poi("noisy", description="noisy")
    quiet = _poi("quiet", description="quiet")
    scores = score_attenuator([noisy, quiet], pref, config, embed_fn=embed_fn)
    assert abs(scores["noisy"].semantic_penalty - (-0.4)) < 1e-9
    assert scores["quiet"].semantic_penalty == 0.0
    assert scores["noisy"].tag_penalty == 0.0
    print("semantic penalty OK")


def test_semantic_penalty_clamps_positive_similarity() -> None:
    pref = PreferenceProfile.empty()
    pref.negative_soft.dislike_keywords = ["太吵"]
    embed_fn = _embed_from(
        {
            "太吵": [1.0, 0.0, 0.0],
            "opposite": [-1.0, 0.0, 0.0],  # cos -1 -> clamped to 0, no reward
        }
    )
    poi = _poi("opposite", description="opposite")
    scores = score_attenuator([poi], pref, embed_fn=embed_fn)
    assert scores["opposite"].penalty == 0.0
    print("semantic penalty clamp OK")


def test_combined_semantic_and_tag() -> None:
    pref = PreferenceProfile.empty()
    pref.negative_soft.dislike_tags = ["人多"]
    pref.negative_soft.dislike_keywords = ["太吵"]
    config = ScoringConfig()
    # negative_semantic_query_text() = "人多 太吵"
    embed_fn = _embed_from(
        {
            "人多 太吵": [1.0, 0.0, 0.0],
            "bad": [1.0, 0.0, 0.0],
        }
    )
    poi = _poi("bad", description="bad", tags=["人多"])
    scores = score_attenuator([poi], pref, config, embed_fn=embed_fn)
    # semantic -0.4, tag -0.1 -> total -0.5
    assert abs(scores["bad"].semantic_penalty - (-0.4)) < 1e-9
    assert abs(scores["bad"].tag_penalty - (-0.1)) < 1e-9
    assert abs(scores["bad"].penalty - (-0.5)) < 1e-9
    assert scores["bad"].penalty <= 0.0
    print("combined penalty OK")


def test_short_negative_text_skips_semantic() -> None:
    pref = PreferenceProfile.empty()
    pref.negative_soft.dislike_keywords = ["吵"]  # length 1 < default min 2
    # no dislike_tags -> both signals inactive -> zeros, embed not called

    def boom(texts: list[str]) -> list[list[float]]:
        raise AssertionError("embed_fn must not be called below min length")

    scores = score_attenuator([_poi("p")], pref, embed_fn=boom)
    assert scores["p"].penalty == 0.0
    print("short negative skip OK")


def test_empty_pool() -> None:
    assert score_attenuator([], PreferenceProfile.empty()) == {}
    print("empty pool OK")


if __name__ == "__main__":
    test_no_negative_returns_zero_without_embedding()
    test_tag_penalty_counts_overlap()
    test_semantic_penalty_negative_for_disliked()
    test_semantic_penalty_clamps_positive_similarity()
    test_combined_semantic_and_tag()
    test_short_negative_text_skips_semantic()
    test_empty_pool()
    print("ALL TESTS PASSED")
