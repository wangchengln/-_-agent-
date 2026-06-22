"""Structured user preference profile (IRF state P_t).

Maps the paper's four-quadrant preference model:
  positive_hard / positive_soft / negative_hard / negative_soft
"""

from __future__ import annotations

import time
from typing import Self

from pydantic import BaseModel, Field

from domain.types import GeoLocation, VenueType


class PositiveHardConstraints(BaseModel):
    """Hard constraints items must satisfy (Filter tool, violation => -inf)."""

    radius_m: int | None = Field(
        default=None,
        ge=0,
        description="Maximum distance from anchor in meters",
    )
    categories: list[str] = Field(
        default_factory=list,
        description="POI categories/types that must match (empty = no restriction)",
    )
    max_price: float | None = Field(
        default=None,
        ge=0,
        description="Maximum average cost per person (CNY)",
    )
    min_rating: float | None = Field(
        default=None,
        ge=0,
        le=5,
        description="Minimum POI rating (0-5)",
    )
    open_now: bool | None = Field(
        default=None,
        description="Require POI to be open now",
    )
    venue_type: VenueType = Field(
        default=VenueType.ANY,
        description="Indoor/outdoor venue requirement",
    )


class PositiveSoftPreferences(BaseModel):
    """Soft positive preferences (Matcher semantic signal)."""

    tags: list[str] = Field(
        default_factory=list,
        description="Atmosphere/style tags, e.g. 文艺, 亲子, 自然",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Free-form intent keywords for semantic matching",
    )
    cuisine_types: list[str] = Field(
        default_factory=list,
        description="Preferred cuisine types",
    )


class NegativeHardConstraints(BaseModel):
    """Hard exclusions (Filter tool, match => -inf)."""

    exclude_categories: list[str] = Field(
        default_factory=list,
        description="POI categories to exclude entirely, e.g. 商场",
    )
    exclude_poi_ids: list[str] = Field(
        default_factory=list,
        description="Explicit POI ids to never recommend again",
    )
    exclude_tags: list[str] = Field(
        default_factory=list,
        description="Tags that cause hard exclusion when present",
    )


class NegativeSoftPreferences(BaseModel):
    """Soft negative preferences (Attenuator tool penalty)."""

    dislike_tags: list[str] = Field(
        default_factory=list,
        description="Tags that reduce score, e.g. 人多, 网红",
    )
    dislike_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords that reduce score via semantic similarity",
    )


class PreferenceProfile(BaseModel):
    """Full explicit preference state P_t in the IRF loop."""

    version: int = Field(default=1, ge=1)
    anchor: GeoLocation | None = Field(
        default=None,
        description="Search anchor (user location or chosen area center)",
    )
    positive_hard: PositiveHardConstraints = Field(
        default_factory=PositiveHardConstraints
    )
    positive_soft: PositiveSoftPreferences = Field(
        default_factory=PositiveSoftPreferences
    )
    negative_hard: NegativeHardConstraints = Field(
        default_factory=NegativeHardConstraints
    )
    negative_soft: NegativeSoftPreferences = Field(
        default_factory=NegativeSoftPreferences
    )
    updated_at: float = Field(
        default_factory=time.time,
        description="Unix timestamp of last update",
    )
    source_command: str | None = Field(
        default=None,
        description="Natural language command c_t that produced this update",
    )

    @classmethod
    def empty(cls, *, anchor: GeoLocation | None = None) -> Self:
        """Create a blank preference profile."""
        return cls(anchor=anchor)

    @staticmethod
    def _merge_unique(existing: list[str], incoming: list[str]) -> list[str]:
        seen: set[str] = set()
        merged: list[str] = []
        for value in existing + incoming:
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
        return merged

    @staticmethod
    def _pick_tighter_radius(
        current: int | None, incoming: int | None
    ) -> int | None:
        if current is None:
            return incoming
        if incoming is None:
            return current
        return min(current, incoming)

    @staticmethod
    def _pick_stricter_max_price(
        current: float | None, incoming: float | None
    ) -> float | None:
        if current is None:
            return incoming
        if incoming is None:
            return current
        return min(current, incoming)

    @staticmethod
    def _pick_stricter_min_rating(
        current: float | None, incoming: float | None
    ) -> float | None:
        if current is None:
            return incoming
        if incoming is None:
            return current
        return max(current, incoming)

    def merge_with(
        self,
        delta: PreferenceProfile,
        *,
        source_command: str | None = None,
    ) -> Self:
        """Merge a preference delta into the current profile.

        Merge policy (aligned with IRF dynamic memory):
        - Lists: union with deduplication
        - Hard scalars: pick the stricter constraint
        - Anchor: incoming wins when provided
        - venue_type: incoming wins when not ANY
        """
        merged_anchor = delta.anchor or self.anchor

        positive_hard = PositiveHardConstraints(
            radius_m=self._pick_tighter_radius(
                self.positive_hard.radius_m, delta.positive_hard.radius_m
            ),
            categories=self._merge_unique(
                self.positive_hard.categories, delta.positive_hard.categories
            ),
            max_price=self._pick_stricter_max_price(
                self.positive_hard.max_price, delta.positive_hard.max_price
            ),
            min_rating=self._pick_stricter_min_rating(
                self.positive_hard.min_rating, delta.positive_hard.min_rating
            ),
            open_now=(
                delta.positive_hard.open_now
                if delta.positive_hard.open_now is not None
                else self.positive_hard.open_now
            ),
            venue_type=(
                delta.positive_hard.venue_type
                if delta.positive_hard.venue_type != VenueType.ANY
                else self.positive_hard.venue_type
            ),
        )

        positive_soft = PositiveSoftPreferences(
            tags=self._merge_unique(
                self.positive_soft.tags, delta.positive_soft.tags
            ),
            keywords=self._merge_unique(
                self.positive_soft.keywords, delta.positive_soft.keywords
            ),
            cuisine_types=self._merge_unique(
                self.positive_soft.cuisine_types,
                delta.positive_soft.cuisine_types,
            ),
        )

        negative_hard = NegativeHardConstraints(
            exclude_categories=self._merge_unique(
                self.negative_hard.exclude_categories,
                delta.negative_hard.exclude_categories,
            ),
            exclude_poi_ids=self._merge_unique(
                self.negative_hard.exclude_poi_ids,
                delta.negative_hard.exclude_poi_ids,
            ),
            exclude_tags=self._merge_unique(
                self.negative_hard.exclude_tags,
                delta.negative_hard.exclude_tags,
            ),
        )

        negative_soft = NegativeSoftPreferences(
            dislike_tags=self._merge_unique(
                self.negative_soft.dislike_tags,
                delta.negative_soft.dislike_tags,
            ),
            dislike_keywords=self._merge_unique(
                self.negative_soft.dislike_keywords,
                delta.negative_soft.dislike_keywords,
            ),
        )

        return self.model_copy(
            update={
                "anchor": merged_anchor,
                "positive_hard": positive_hard,
                "positive_soft": positive_soft,
                "negative_hard": negative_hard,
                "negative_soft": negative_soft,
                "updated_at": time.time(),
                "source_command": source_command or delta.source_command,
            }
        )

    def positive_soft_query_text(self) -> str:
        """Soft-preference-only text for Matcher embedding.

        Excludes city/category (those are location context and hard filters,
        not semantic vibe signals), so the semantic Matcher engages only when
        the user expressed a genuine soft preference.
        """
        parts: list[str] = []
        parts.extend(self.positive_soft.tags)
        parts.extend(self.positive_soft.keywords)
        parts.extend(self.positive_soft.cuisine_types)
        return " ".join(part.strip() for part in parts if part.strip())

    def semantic_query_text(self) -> str:
        """Build a text blob for embedding-based Matcher scoring."""
        parts: list[str] = []
        parts.extend(self.positive_soft.tags)
        parts.extend(self.positive_soft.keywords)
        parts.extend(self.positive_soft.cuisine_types)
        if self.positive_hard.categories:
            parts.append("类别:" + ",".join(self.positive_hard.categories))
        if self.anchor and self.anchor.city:
            parts.append(f"城市:{self.anchor.city}")
        return " ".join(part.strip() for part in parts if part.strip())

    def negative_semantic_query_text(self) -> str:
        """Build a text blob for Attenuator semantic penalty."""
        parts: list[str] = []
        parts.extend(self.negative_soft.dislike_tags)
        parts.extend(self.negative_soft.dislike_keywords)
        parts.extend(self.negative_hard.exclude_tags)
        parts.extend(self.negative_hard.exclude_categories)
        return " ".join(part.strip() for part in parts if part.strip())

    @staticmethod
    def _format_list(values: list[str]) -> str | None:
        cleaned = [value.strip() for value in values if value.strip()]
        if not cleaned:
            return None
        return ",".join(cleaned)

    def to_parser_context(self) -> str:
        """Compact four-quadrant summary for Parser Agent prompt injection."""
        lines: list[str] = ["[当前偏好 P_t]"]

        if self.anchor:
            anchor_parts: list[str] = []
            if self.anchor.city:
                anchor_parts.append(self.anchor.city)
            if self.anchor.address:
                anchor_parts.append(self.anchor.address)
            elif self.anchor.lat is not None and self.anchor.lng is not None:
                anchor_parts.append(f"{self.anchor.lat:.4f},{self.anchor.lng:.4f}")
            if anchor_parts:
                lines.append("锚点: " + " · ".join(anchor_parts))

        hard_parts: list[str] = []
        if self.positive_hard.radius_m is not None:
            hard_parts.append(f"半径{self.positive_hard.radius_m}m")
        if categories := self._format_list(self.positive_hard.categories):
            hard_parts.append(f"类别:{categories}")
        if self.positive_hard.max_price is not None:
            hard_parts.append(f"最高人均{self.positive_hard.max_price:g}元")
        if self.positive_hard.min_rating is not None:
            hard_parts.append(f"最低评分{self.positive_hard.min_rating:g}")
        if self.positive_hard.open_now is True:
            hard_parts.append("营业中")
        if self.positive_hard.venue_type.value != "any":
            hard_parts.append(f"场内外:{self.positive_hard.venue_type.value}")
        if hard_parts:
            lines.append("正向硬约束: " + " | ".join(hard_parts))

        soft_parts: list[str] = []
        if tags := self._format_list(self.positive_soft.tags):
            soft_parts.append(f"标签:{tags}")
        if keywords := self._format_list(self.positive_soft.keywords):
            soft_parts.append(f"关键词:{keywords}")
        if cuisines := self._format_list(self.positive_soft.cuisine_types):
            soft_parts.append(f"菜系:{cuisines}")
        if soft_parts:
            lines.append("正向软偏好: " + " | ".join(soft_parts))

        neg_hard_parts: list[str] = []
        if excluded := self._format_list(self.negative_hard.exclude_categories):
            neg_hard_parts.append(f"排除类别:{excluded}")
        if poi_ids := self._format_list(self.negative_hard.exclude_poi_ids):
            neg_hard_parts.append(f"排除POI:{poi_ids}")
        if ex_tags := self._format_list(self.negative_hard.exclude_tags):
            neg_hard_parts.append(f"排除标签:{ex_tags}")
        if neg_hard_parts:
            lines.append("负向硬排除: " + " | ".join(neg_hard_parts))

        neg_soft_parts: list[str] = []
        if dislike_tags := self._format_list(self.negative_soft.dislike_tags):
            neg_soft_parts.append(f"不喜标签:{dislike_tags}")
        if dislike_kw := self._format_list(self.negative_soft.dislike_keywords):
            neg_soft_parts.append(f"不喜关键词:{dislike_kw}")
        if neg_soft_parts:
            lines.append("负向软惩罚: " + " | ".join(neg_soft_parts))

        if len(lines) == 1:
            lines.append("(空白偏好，用户尚未表达约束)")
        return "\n".join(lines)
