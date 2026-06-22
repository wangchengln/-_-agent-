#!/usr/bin/env python3
"""Tests for recsys embedding service (Block B) — no real API key required."""

from __future__ import annotations

from recsys import embeddings
from recsys.embeddings import (
    batch_embed_with_cache,
    cosine_similarity,
    embed_text,
    embed_texts,
)


class FakeEmbedder:
    """Deterministic stand-in for the OpenAI embedding client.

    Records each batch it receives so tests can assert batching behaviour, and
    returns a stable vector per text so identical inputs are identical vectors.
    """

    def __init__(self) -> None:
        self.batches: list[list[str]] = []

    def get_text_embedding_batch(self, texts: list[str]) -> list[list[float]]:
        self.batches.append(list(texts))
        return [self._vector(text) for text in texts]

    @staticmethod
    def _vector(text: str) -> list[float]:
        vec = [0.0] * 8
        for index, char in enumerate(text):
            vec[index % 8] += (ord(char) % 17) / 17.0
        return vec


def _install_fake() -> FakeEmbedder:
    fake = FakeEmbedder()
    embeddings.set_embedder(fake)
    embeddings.reset_embedding_cache()
    return fake


def test_embed_texts_empty_returns_empty() -> None:
    _install_fake()
    assert embed_texts([]) == []
    print("embed_texts empty OK")


def test_embed_texts_preserves_order_and_count() -> None:
    _install_fake()
    texts = ["武康路", "西岸美术馆", "徐汇滨江"]
    vectors = embed_texts(texts)
    assert len(vectors) == len(texts)
    assert vectors[0] == FakeEmbedder._vector("武康路")
    print("embed_texts order/count OK")


def test_embed_texts_batches_at_most_10() -> None:
    fake = _install_fake()
    texts = [f"poi-{i}" for i in range(25)]
    vectors = embed_texts(texts)
    assert len(vectors) == 25
    assert len(fake.batches) == 3
    assert [len(b) for b in fake.batches] == [10, 10, 5]
    assert all(len(b) <= 10 for b in fake.batches)
    print("embed_texts batching OK")


def test_embed_text_single() -> None:
    _install_fake()
    vector = embed_text("西岸美术馆")
    assert vector == FakeEmbedder._vector("西岸美术馆")
    assert embed_text("") != vector
    print("embed_text single OK")


def test_cache_dedupes_requests() -> None:
    fake = _install_fake()
    first = batch_embed_with_cache(["a", "a", "b"])
    assert len(first) == 3
    assert first[0] == first[1]
    # Only unique strings reach the embedder.
    assert sorted(t for batch in fake.batches for t in batch) == ["a", "b"]

    # Second call for an already-cached string makes no new request.
    before = sum(len(b) for b in fake.batches)
    again = batch_embed_with_cache(["a"])
    after = sum(len(b) for b in fake.batches)
    assert again[0] == first[0]
    assert before == after
    print("cache dedupe OK")


def test_cosine_identical_is_one() -> None:
    vec = [0.3, 0.4, 0.5]
    assert abs(cosine_similarity(vec, vec) - 1.0) < 1e-9
    print("cosine identical OK")


def test_cosine_orthogonal_is_zero() -> None:
    assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-9
    print("cosine orthogonal OK")


def test_cosine_opposite_is_minus_one() -> None:
    assert abs(cosine_similarity([1.0, 0.0], [-1.0, 0.0]) + 1.0) < 1e-9
    print("cosine opposite OK")


def test_cosine_empty_returns_zero() -> None:
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([1.0], []) == 0.0
    print("cosine empty OK")


def test_cosine_zero_vector_returns_zero() -> None:
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0
    print("cosine zero-vector OK")


def test_cosine_dimension_mismatch_raises() -> None:
    try:
        cosine_similarity([1.0, 2.0], [1.0])
    except ValueError:
        print("cosine dim-mismatch guard OK")
        return
    raise AssertionError("expected ValueError on dimension mismatch")


def test_cosine_in_range() -> None:
    a = FakeEmbedder._vector("文艺 室外 CityWalk")
    b = FakeEmbedder._vector("商场 室内 网红")
    score = cosine_similarity(a, b)
    assert -1.0 <= score <= 1.0
    print("cosine range OK")


if __name__ == "__main__":
    test_embed_texts_empty_returns_empty()
    test_embed_texts_preserves_order_and_count()
    test_embed_texts_batches_at_most_10()
    test_embed_text_single()
    test_cache_dedupes_requests()
    test_cosine_identical_is_one()
    test_cosine_orthogonal_is_zero()
    test_cosine_opposite_is_minus_one()
    test_cosine_empty_returns_zero()
    test_cosine_zero_vector_returns_zero()
    test_cosine_dimension_mismatch_raises()
    test_cosine_in_range()
    print("ALL TESTS PASSED")
