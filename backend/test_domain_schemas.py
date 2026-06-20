#!/usr/bin/env python3
"""Smoke tests for domain data contracts (Module B)."""

import json
from pathlib import Path

from domain import (
    GeoLocation,
    PreferenceProfile,
    RecommendationFeed,
    parse_amap_poi,
    parse_amap_pois,
)


def test_fixture_round_trip() -> None:
    fixture_path = Path(__file__).parent / "domain" / "fixtures" / "sample_feed.json"
    feed = RecommendationFeed.model_validate_json(
        fixture_path.read_text(encoding="utf-8")
    )
    assert len(feed.items) == 3
    assert feed.scores["B001A0LXYZ"] == 0.92
    assert feed.preference_snapshot.positive_soft.tags[0] == "文艺"
    print("fixture OK:", feed.items[0].item.name)


def test_parse_amap_poi() -> None:
    raw = {
        "id": "B0TEST001",
        "name": "测试咖啡馆",
        "type": "餐饮服务;咖啡厅",
        "typecode": "050500",
        "address": "上海市静安区南京西路100号",
        "location": "121.45,31.23",
        "distance": "520",
        "tel": "021-88888888",
        "tag": "咖啡;安静;WiFi",
        "biz_ext": {"rating": "4.3", "cost": "45.00"},
    }
    poi = parse_amap_poi(raw, anchor_city="上海")
    assert poi.cost_numeric == 45.0
    assert poi.distance_m == 520.0
    assert "安静" in poi.tags
    assert "评分4.3" in poi.description
    print("parse_amap_poi OK:", poi.name)

    skipped = parse_amap_pois([raw, {"id": "", "name": "bad"}])
    assert len(skipped) == 1
    print("parse_amap_pois skip-invalid OK")


def test_preference_merge() -> None:
    base = PreferenceProfile.empty(
        anchor=GeoLocation(lng=121.47, lat=31.23, city="上海")
    )
    base.positive_hard.radius_m = 8000
    base.positive_soft.tags = ["文艺"]
    base.negative_soft.dislike_tags = ["人多"]

    delta = PreferenceProfile(
        positive_hard=base.positive_hard.model_copy(
            update={"radius_m": 3000, "max_price": 100}
        ),
        positive_soft=base.positive_soft.model_copy(update={"tags": ["CityWalk"]}),
        negative_hard=base.negative_hard.model_copy(
            update={"exclude_categories": ["商场"]}
        ),
        negative_soft=base.negative_soft.model_copy(
            update={"dislike_keywords": ["太吵"]}
        ),
        source_command="别太远，预算100以内",
    )
    merged = base.merge_with(delta)
    assert merged.positive_hard.radius_m == 3000
    assert merged.positive_hard.max_price == 100
    assert set(merged.positive_soft.tags) == {"文艺", "CityWalk"}
    assert merged.negative_hard.exclude_categories == ["商场"]
    assert merged.negative_soft.dislike_keywords == ["太吵"]
    print("merge OK:", merged.semantic_query_text())


def test_feed_builder() -> None:
    raw = {
        "id": "B0TEST001",
        "name": "测试咖啡馆",
        "type": "餐饮服务;咖啡厅",
        "location": "121.45,31.23",
    }
    poi = parse_amap_poi(raw, anchor_city="上海")
    merged = PreferenceProfile.empty(
        anchor=GeoLocation(lng=121.47, lat=31.23, city="上海")
    )
    feed = RecommendationFeed.from_poi_items(
        [poi], round=2, preference_snapshot=merged, k=3
    )
    assert feed.round == 2
    assert feed.items[0].rank == 1
    print("from_poi_items OK")


if __name__ == "__main__":
    test_fixture_round_trip()
    test_parse_amap_poi()
    test_preference_merge()
    test_feed_builder()
    print("ALL TESTS PASSED")
