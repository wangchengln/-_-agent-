#!/usr/bin/env python3
"""CLI helper to plan a recommendation feed from structured preference JSON."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv

load_dotenv()

from domain import IRFSessionState, PreferenceProfile, RecommendationFeed
from graph.planner_agent import (
    PlannerAgent,
    PlannerError,
    PlannerInput,
    planner_agent,
)
from graph.session_manager import SessionManager


def _load_preference_from_file(path: str) -> PreferenceProfile:
    return PreferenceProfile.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def _load_preference_from_feed(path: str) -> PreferenceProfile:
    feed = RecommendationFeed.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )
    return feed.preference_snapshot


def _resolve_state(args: argparse.Namespace, manager: SessionManager | None) -> IRFSessionState:
    if manager is not None and args.session_id:
        return manager.get_irf_state(args.session_id)

    if args.state:
        return IRFSessionState.from_session_dict(
            json.loads(Path(args.state).read_text(encoding="utf-8"))
        )

    return IRFSessionState.empty()


def _resolve_preference(args: argparse.Namespace, state: IRFSessionState) -> PreferenceProfile:
    if args.preference:
        return _load_preference_from_file(args.preference)

    if args.feed:
        if not args.extract_preference_from_feed:
            raise ValueError(
                "pass --extract-preference-from-feed when using --feed as preference source"
            )
        return _load_preference_from_feed(args.feed)

    if state.preference.anchor or state.preference.positive_hard.categories:
        return state.preference

    raise ValueError(
        "no preference source: provide --preference, --feed with "
        "--extract-preference-from-feed, --state, or --session-id with IRF preference"
    )


async def _run(args: argparse.Namespace) -> int:
    manager: SessionManager | None = None
    if args.session_id:
        base_dir = Path(args.base_dir).resolve()
        manager = SessionManager()
        manager.initialize(base_dir)
        if not manager._session_path(args.session_id).exists():
            manager.create_session(args.session_id)

    state = _resolve_state(args, manager)

    try:
        preference = _resolve_preference(args, state)
    except ValueError as exc:
        print(f"Preference error: {exc}", file=sys.stderr)
        return 1

    round_index = args.round if args.round is not None else state.round
    user_command = args.command or preference.source_command

    planner_input = PlannerInput(
        preference=preference,
        round=round_index,
        user_command=user_command,
        k=args.k,
    )

    agent = planner_agent if args.use_default_agent else PlannerAgent()

    try:
        feed = await agent.plan(planner_input)
    except PlannerError as exc:
        print(f"Planner failed: {exc}", file=sys.stderr)
        return 1

    if manager is not None and args.session_id:
        irf_state = manager.get_irf_state(args.session_id)
        irf_state = irf_state.model_copy(
            update={
                "preference": preference,
                "current_feed": feed,
            }
        )
        manager.save_irf_state(args.session_id, irf_state)
        next_state = irf_state
    else:
        next_state = state.model_copy(
            update={
                "preference": preference,
                "current_feed": feed,
            }
        )

    result = {
        "feed": feed.model_dump(mode="json"),
        "next_state": next_state.to_session_dict(),
    }

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plan IRF recommendation feed from structured preference"
    )
    parser.add_argument(
        "--preference",
        help="Path to PreferenceProfile JSON",
    )
    parser.add_argument(
        "--feed",
        help="Path to RecommendationFeed JSON (use with --extract-preference-from-feed)",
    )
    parser.add_argument(
        "--extract-preference-from-feed",
        action="store_true",
        help="Read preference_snapshot from --feed instead of a standalone preference file",
    )
    parser.add_argument(
        "--state",
        help="Path to standalone IRF state JSON (uses embedded preference when no --preference)",
    )
    parser.add_argument(
        "--session-id",
        help="Load preference from and persist feed to sessions/{session-id}.json",
    )
    parser.add_argument(
        "--command",
        help="User command c_t recorded on the feed (defaults to preference.source_command)",
    )
    parser.add_argument(
        "--round",
        type=int,
        help="IRF round index for the feed (defaults to session/state round or 1)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Top-K feed size (default: 5)",
    )
    parser.add_argument(
        "--base-dir",
        default=str(Path(__file__).resolve().parent.parent),
        help="Backend base dir containing sessions/ (default: backend/)",
    )
    parser.add_argument(
        "--use-default-agent",
        action="store_true",
        help="Use the module-level planner_agent singleton (default: fresh PlannerAgent)",
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
