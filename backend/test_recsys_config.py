#!/usr/bin/env python3
"""Tests for recsys scaffolding (Block A): ScoringConfig + type aliases."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from domain.poi import POIItem
from recsys import (
    DEFAULT_SCORING_CONFIG,
    CandidatePool,
    EmbeddingVector,
    ScoringConfig,
)

GOLDEN_FEED = Path(__file__).parent / "domain" / "fixtures" / "golden_feed.json"


def test_default_config_values() -> None:
    config = ScoringConfig()
    assert config.k == 5
    assert config.default_radius_m == 5000
    assert config.max_candidates == 80
    assert config.alpha_semantic == 0.65
    assert config.alpha_collaborative == 0.35
    assert config.beta_attenuator == 0.4
    assert config.min_semantic_query_len == 2
    print("default config values OK")


def test_default_singleton_is_frozen() -> None:
    assert isinstance(DEFAULT_SCORING_CONFIG, ScoringConfig)
    try:
        DEFAULT_SCORING_CONFIG.k = 10  # type: ignore[misc]
    except ValidationError:
        print("frozen config rejects mutation OK")
        return
    raise AssertionError("frozen config should reject attribute assignment")


def test_model_copy_override() -> None:
    config = ScoringConfig().model_copy(update={"k": 8, "max_candidates": 40})
    assert config.k == 8
    assert config.max_candidates == 40
    assert config.alpha_semantic == 0.65
    print("model_copy override OK")


def test_matcher_weights_must_sum_to_one() -> None:
    try:
        ScoringConfig(alpha_semantic=0.7, alpha_collaborative=0.5)
    except ValidationError:
        print("matcher weight sum guard OK")
        return
    raise AssertionError("expected ValidationError for matcher weights != 1.0")


def test_collab_weights_must_sum_to_one() -> None:
    try:
        ScoringConfig(collab_rating_weight=0.5, collab_distance_weight=0.3)
    except ValidationError:
        print("collaborative weight sum guard OK")
        return
    raise AssertionError("expected ValidationError for collab weights != 1.0")


def test_negative_field_rejected() -> None:
    try:
        ScoringConfig(k=0)
    except ValidationError:
        print("k >= 1 guard OK")
        return
    raise AssertionError("expected ValidationError for k=0")


def test_type_aliases_usable() -> None:
    pool: CandidatePool = []
    vector: EmbeddingVector = [0.1, 0.2, 0.3]
    assert pool == []
    assert len(vector) == 3
    assert CandidatePool == list[POIItem]
    print("type aliases OK")


def test_golden_fixture_exists_and_valid() -> None:
    assert GOLDEN_FEED.exists(), "golden_feed.json fixture missing"
    data = json.loads(GOLDEN_FEED.read_text(encoding="utf-8"))
    assert data["items"], "golden feed should contain items"
    assert "breakdown" in data["items"][0], "golden feed items need score breakdown"
    print("golden fixture OK")


if __name__ == "__main__":
    test_default_config_values()
    test_default_singleton_is_frozen()
    test_model_copy_override()
    test_matcher_weights_must_sum_to_one()
    test_collab_weights_must_sum_to_one()
    test_negative_field_rejected()
    test_type_aliases_usable()
    test_golden_fixture_exists_and_valid()
    print("ALL TESTS PASSED")
