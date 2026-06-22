"""Embedding service for the recsys Matcher / Attenuator stages.

Provides a thin, mockable wrapper around an OpenAI-compatible embedding API
(DashScope Bailian, OpenAI, proxies, etc.). Configuration mirrors the rest of
the backend: ``EMBEDDING_MODEL``, ``OPENAI_API_KEY``, ``OPENAI_BASE_URL``.

Uses the ``openai`` SDK directly (not LlamaIndex) so custom model names such as
``text-embedding-v4`` work without enum validation errors.
"""

from __future__ import annotations

import math
import os
from typing import Any, Protocol

from recsys.types import EmbeddingVector

# DashScope compatible-mode caps each request at 10 inputs.
_EMBED_BATCH_SIZE = 10


class EmbeddingClient(Protocol):
    """Protocol satisfied by the real client and test fakes."""

    def get_text_embedding_batch(self, texts: list[str]) -> list[EmbeddingVector]: ...


class _OpenAICompatibleEmbedder:
    """Thin adapter over ``openai.OpenAI().embeddings.create``."""

    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self._model = model

    def get_text_embedding_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        response = self._client.embeddings.create(
            input=texts,
            model=self._model,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        return [list(item.embedding) for item in ordered]


_embedder: EmbeddingClient | None = None
_embedding_cache: dict[str, EmbeddingVector] = {}


def get_embedder() -> EmbeddingClient:
    """Return the process-wide embedding client, building it on first use."""
    global _embedder
    if _embedder is None:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv(
                "OPENAI_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
        )
        model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        _embedder = _OpenAICompatibleEmbedder(client, model)
    return _embedder


def set_embedder(embedder: EmbeddingClient | None) -> None:
    """Inject an embedder (used by tests to bypass the real client)."""
    global _embedder
    _embedder = embedder


def reset_embedding_cache() -> None:
    """Drop the in-memory text->vector cache."""
    _embedding_cache.clear()


def embed_texts(texts: list[str]) -> list[EmbeddingVector]:
    """Embed a list of texts, returning one vector per input (order preserved).

    Empty input yields an empty list. Requests are split into batches of at
    most :data:`_EMBED_BATCH_SIZE`.
    """
    if not texts:
        return []

    embedder = get_embedder()
    vectors: list[EmbeddingVector] = []
    for start in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[start : start + _EMBED_BATCH_SIZE]
        vectors.extend(embedder.get_text_embedding_batch(batch))
    return vectors


def embed_text(text: str) -> EmbeddingVector:
    """Embed a single text; returns ``[]`` for empty input."""
    result = embed_texts([text])
    return result[0] if result else []


def batch_embed_with_cache(texts: list[str]) -> list[EmbeddingVector]:
    """Embed texts, reusing cached vectors for repeated identical strings.

    Useful for POI descriptions that recur across IRF rounds. Only previously
    unseen, de-duplicated strings are sent to the model.
    """
    if not texts:
        return []

    missing = [text for text in dict.fromkeys(texts) if text not in _embedding_cache]
    if missing:
        fresh = embed_texts(missing)
        for text, vector in zip(missing, fresh):
            _embedding_cache[text] = vector

    return [_embedding_cache[text] for text in texts]


def cosine_similarity(vec_a: EmbeddingVector, vec_b: EmbeddingVector) -> float:
    """Cosine similarity in ``[-1.0, 1.0]``.

    Returns ``0.0`` when either vector is empty or has zero magnitude. Raises
    ``ValueError`` on dimension mismatch (a programming error, not a data gap).
    """
    if not vec_a or not vec_b:
        return 0.0
    if len(vec_a) != len(vec_b):
        raise ValueError(
            f"vector dimension mismatch: {len(vec_a)} != {len(vec_b)}"
        )

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += a * b
        norm_a += a * a
        norm_b += b * b

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    similarity = dot / (math.sqrt(norm_a) * math.sqrt(norm_b))
    return max(-1.0, min(1.0, similarity))
