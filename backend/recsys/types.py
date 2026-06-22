"""Shared type aliases for the recsys scoring pipeline.

Kept separate from ``config`` so every stage (Filter / Matcher / Attenuator /
Aggregator) can depend on lightweight aliases without importing tuning state.
"""

from __future__ import annotations

from domain.poi import POIItem

CandidatePool = list[POIItem]
"""Pool of candidate POIs (the paper's item set I) flowing through scoring."""

EmbeddingVector = list[float]
"""Dense embedding vector produced by the embedding service."""
