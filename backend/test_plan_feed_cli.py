#!/usr/bin/env python3
"""CLI helper tests for plan_feed.py (Block I) — no network."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from scripts.plan_feed import (  # noqa: E402
    _load_preference_from_feed,
    _resolve_preference,
)
from domain.irf_state import IRFSessionState
from domain.preference import PreferenceProfile
import argparse


GOLDEN = _BACKEND / "domain" / "fixtures" / "golden_feed.json"


def test_load_preference_from_feed() -> None:
    pref = _load_preference_from_feed(str(GOLDEN))
    assert pref.anchor is not None
    assert pref.anchor.city == "上海"
    assert "文艺" in pref.positive_soft.tags
    print("load preference from feed OK")


def test_resolve_preference_from_file_arg() -> None:
    pref = PreferenceProfile.empty()
    pref.positive_soft.tags = ["测试"]
    tmp = _BACKEND / "sessions" / "_test_pref.json"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(pref.model_dump_json(), encoding="utf-8")
    try:
        args = argparse.Namespace(
            preference=str(tmp),
            feed=None,
            extract_preference_from_feed=False,
        )
        resolved = _resolve_preference(args, IRFSessionState.empty())
        assert resolved.positive_soft.tags == ["测试"]
    finally:
        tmp.unlink(missing_ok=True)
    print("resolve --preference OK")


def test_resolve_preference_requires_extract_flag() -> None:
    args = argparse.Namespace(
        preference=None,
        feed=str(GOLDEN),
        extract_preference_from_feed=False,
    )
    try:
        _resolve_preference(args, IRFSessionState.empty())
    except ValueError as exc:
        assert "extract-preference-from-feed" in str(exc)
        print("extract flag guard OK")
        return
    raise AssertionError("expected ValueError")


if __name__ == "__main__":
    test_load_preference_from_feed()
    test_resolve_preference_from_file_arg()
    test_resolve_preference_requires_extract_flag()
    print("ALL TESTS PASSED")
