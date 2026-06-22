#!/usr/bin/env python3
"""Tests for IRF session persistence (Module D)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from domain import (
    IRFSessionState,
    ParserOutput,
    PreferenceProfile,
    RecommendationFeed,
)
from graph.session_manager import SessionManager

FIXTURE_FEED = Path(__file__).parent.parent / "domain" / "fixtures" / "sample_feed.json"


def _make_manager(tmp_dir: Path) -> SessionManager:
    manager = SessionManager()
    manager.initialize(tmp_dir)
    return manager


def test_get_irf_state_empty_session() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _make_manager(Path(tmp))
        state = manager.get_irf_state("new-session")
        assert state.round == 1
        assert state.preference.positive_soft.tags == []
        assert state.current_feed is None
        print("empty irf state OK")


def test_legacy_session_without_irf() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _make_manager(Path(tmp))
        manager.create_session("legacy")
        manager.save_message("legacy", "user", "hello")

        state = manager.get_irf_state("legacy")
        assert state.round == 1
        assert state.command_history == []

        raw = manager._read_file("legacy")
        assert "irf" not in raw
        print("legacy session read OK")


def test_save_and_reload_irf_state() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _make_manager(Path(tmp))
        feed = RecommendationFeed.model_validate_json(
            FIXTURE_FEED.read_text(encoding="utf-8")
        )
        state = IRFSessionState(
            round=2,
            preference=feed.preference_snapshot,
            current_feed=feed,
            command_history=["第一轮命令"],
        )

        manager.create_session("irf-test")
        manager.save_irf_state("irf-test", state)
        restored = manager.get_irf_state("irf-test")

        assert restored.round == 2
        assert restored.preference.positive_soft.tags == feed.preference_snapshot.positive_soft.tags
        assert restored.current_feed is not None
        assert restored.current_feed.items[0].item.name == "武康路历史文化名街"
        assert restored.command_history == ["第一轮命令"]
        print("save/reload irf OK")


def test_apply_parser_result() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _make_manager(Path(tmp))
        feed = RecommendationFeed.model_validate_json(
            FIXTURE_FEED.read_text(encoding="utf-8")
        )
        manager.create_session("parse-test")
        manager.save_irf_state(
            "parse-test",
            IRFSessionState(
                round=1,
                preference=feed.preference_snapshot,
                current_feed=feed,
            ),
        )

        new_pref = feed.preference_snapshot.model_copy(deep=True)
        new_pref.positive_hard.radius_m = 3000
        output = ParserOutput(
            preference=new_pref,
            intent_summary="半径缩小到3公里",
        )

        next_state = manager.apply_parser_result("parse-test", "3公里内", output)
        assert next_state.round == 2
        assert next_state.preference.positive_hard.radius_m == 3000
        assert next_state.command_history == ["3公里内"]
        assert next_state.current_feed is not None
        assert next_state.current_feed.items[0].item.name == "武康路历史文化名街"

        reloaded = manager.get_irf_state("parse-test")
        assert reloaded.round == 2
        assert reloaded.preference.positive_hard.radius_m == 3000
        print("apply_parser_result OK")


def test_save_irf_feed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _make_manager(Path(tmp))
        feed = RecommendationFeed.model_validate_json(
            FIXTURE_FEED.read_text(encoding="utf-8")
        )
        manager.create_session("feed-test")
        manager.save_irf_state("feed-test", IRFSessionState.empty())

        next_state = manager.save_irf_feed("feed-test", feed)
        assert next_state.current_feed is not None
        assert len(next_state.current_feed.items) == 3

        reloaded = manager.get_irf_state("feed-test")
        assert reloaded.current_feed is not None
        print("save_irf_feed OK")


def test_legacy_preference_state_alias() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _make_manager(Path(tmp))
        session_path = manager._session_path("alias-test")
        session_path.write_text(
            json.dumps(
                {
                    "title": "Alias",
                    "created_at": 1,
                    "updated_at": 2,
                    "messages": [],
                    "irf": {
                        "round": 1,
                        "preference_state": PreferenceProfile.empty(
                            anchor=None
                        ).model_dump(mode="json"),
                        "command_history": [],
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        state = manager.get_irf_state("alias-test")
        assert state.preference.version == 1
        print("preference_state alias OK")


def test_irf_coexists_with_messages() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _make_manager(Path(tmp))
        manager.create_session("combo")
        manager.save_message("combo", "user", "帮我规划周末")
        manager.save_irf_state("combo", IRFSessionState.empty())

        messages = manager.load_session("combo")
        irf = manager.get_irf_state("combo")
        raw = manager._read_file("combo")

        assert len(messages) == 1
        assert messages[0]["content"] == "帮我规划周末"
        assert irf.round == 1
        assert "irf" in raw
        assert len(raw["messages"]) == 1
        print("irf + messages coexist OK")


def test_messages_preserved_after_irf_commit() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _make_manager(Path(tmp))
        feed = RecommendationFeed.model_validate_json(
            FIXTURE_FEED.read_text(encoding="utf-8")
        )
        manager.create_session("commit-msg")
        manager.save_message("commit-msg", "user", "上海周末")

        prior = IRFSessionState.empty()
        output = ParserOutput(
            preference=feed.preference_snapshot,
            intent_summary="上海文艺周末",
        )
        final = manager.commit_irf_round(
            "commit-msg", prior, "上海周末", output, feed
        )

        assert final.round == 2
        assert manager.load_session("commit-msg")[0]["content"] == "上海周末"
        assert manager.get_irf_state("commit-msg").current_feed is not None
        print("messages preserved after commit_irf_round OK")


def test_irf_preserved_after_save_message() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _make_manager(Path(tmp))
        feed = RecommendationFeed.model_validate_json(
            FIXTURE_FEED.read_text(encoding="utf-8")
        )
        manager.create_session("msg-after-irf")
        manager.save_irf_state(
            "msg-after-irf",
            IRFSessionState(round=2, preference=feed.preference_snapshot, current_feed=feed),
        )
        manager.save_message("msg-after-irf", "assistant", "推荐已更新")

        irf = manager.get_irf_state("msg-after-irf")
        assert irf.round == 2
        assert irf.current_feed is not None
        assert len(manager.load_session("msg-after-irf")) == 1
        print("irf preserved after save_message OK")


def test_irf_preserved_after_compress_history() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _make_manager(Path(tmp))
        feed = RecommendationFeed.model_validate_json(
            FIXTURE_FEED.read_text(encoding="utf-8")
        )
        manager.create_session("compress-irf")
        manager.save_message("compress-irf", "user", "第一条")
        manager.save_message("compress-irf", "assistant", "回复")
        manager.save_irf_state(
            "compress-irf",
            IRFSessionState(round=2, preference=feed.preference_snapshot, current_feed=feed),
        )

        manager.compress_history("compress-irf", "摘要", num_to_remove=2)

        irf = manager.get_irf_state("compress-irf")
        raw = manager._read_file("compress-irf")
        assert irf.round == 2
        assert irf.current_feed is not None
        assert raw.get("compressed_context") == "摘要"
        assert raw["messages"] == []
        print("irf preserved after compress_history OK")


def test_commit_irf_round_single_write() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _make_manager(Path(tmp))
        feed = RecommendationFeed.model_validate_json(
            FIXTURE_FEED.read_text(encoding="utf-8")
        )
        manager.create_session("commit-once")
        prior = IRFSessionState(
            round=1,
            preference=feed.preference_snapshot,
            command_history=[],
        )
        output = ParserOutput(
            preference=feed.preference_snapshot.model_copy(
                update={"positive_hard": feed.preference_snapshot.positive_hard.model_copy(
                    update={"radius_m": 2000}
                )}
            ),
            intent_summary="半径2公里",
        )

        final = manager.commit_irf_round(
            "commit-once", prior, "2公里内", output, feed
        )
        assert final.round == 2
        assert final.preference.positive_hard.radius_m == 2000
        assert final.command_history == ["2公里内"]
        assert final.current_feed is not None

        reloaded = manager.get_irf_state("commit-once")
        assert reloaded.round == 2
        assert reloaded.preference.positive_hard.radius_m == 2000
        print("commit_irf_round OK")


if __name__ == "__main__":
    test_get_irf_state_empty_session()
    test_legacy_session_without_irf()
    test_save_and_reload_irf_state()
    test_apply_parser_result()
    test_save_irf_feed()
    test_legacy_preference_state_alias()
    test_irf_coexists_with_messages()
    test_messages_preserved_after_irf_commit()
    test_irf_preserved_after_save_message()
    test_irf_preserved_after_compress_history()
    test_commit_irf_round_single_write()
    print("ALL MODULE D TESTS PASSED")
