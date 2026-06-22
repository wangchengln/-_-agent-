#!/usr/bin/env python3
"""CLI helper to parse a travel command into structured preference JSON."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from domain import IRFSessionState, RecommendationFeed
from graph.parser_agent import ParserAgent, ParserAgentError
from graph.session_manager import SessionManager


def _load_feed(path: str | None) -> RecommendationFeed | None:
    if not path:
        return None
    return RecommendationFeed.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def _resolve_state(args: argparse.Namespace, manager: SessionManager | None) -> IRFSessionState:
    if manager is not None and args.session_id:
        return manager.get_irf_state(args.session_id)

    state = IRFSessionState.empty()
    if args.state:
        state = IRFSessionState.from_session_dict(
            json.loads(Path(args.state).read_text(encoding="utf-8"))
        )
    return state


async def _run(args: argparse.Namespace) -> int:
    manager: SessionManager | None = None
    if args.session_id:
        base_dir = Path(args.base_dir).resolve()
        manager = SessionManager()
        manager.initialize(base_dir)
        if not manager._session_path(args.session_id).exists():
            manager.create_session(args.session_id)

    feed = _load_feed(args.feed)
    state = _resolve_state(args, manager)
    if feed is not None:
        state = state.model_copy(update={"current_feed": feed})

    parser_input = state.build_parser_input(args.command)
    agent = ParserAgent()

    try:
        output = await agent.parse(parser_input, max_feed_items=args.max_feed_items)
    except ParserAgentError as exc:
        print(f"Parser failed: {exc}", file=sys.stderr)
        return 1

    if manager is not None and args.session_id:
        next_state = manager.apply_parser_result(args.session_id, args.command, output)
    else:
        next_state = state.apply_parser_output(args.command, output)

    result = {
        "parser_output": output.model_dump(mode="json"),
        "next_state": next_state.to_session_dict(),
    }

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse IRF travel command")
    parser.add_argument("--command", required=True, help="User command c_t")
    parser.add_argument("--feed", help="Path to RecommendationFeed JSON fixture")
    parser.add_argument("--state", help="Path to standalone IRF state JSON")
    parser.add_argument(
        "--session-id",
        help="Persist result to sessions/{session-id}.json via SessionManager",
    )
    parser.add_argument(
        "--base-dir",
        default=str(Path(__file__).resolve().parent.parent),
        help="Backend base dir containing sessions/ (default: backend/)",
    )
    parser.add_argument("--max-feed-items", type=int, default=5)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
