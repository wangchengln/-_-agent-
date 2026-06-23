#!/usr/bin/env python3
"""CLI helper to build a weekend itinerary from session feed POIs (Day 6.4).

Examples:
  python scripts/build_itinerary.py --session-id demo --pois B001A0LXYZ,B002B1MNPQ
  python scripts/build_itinerary.py --feed domain/fixtures/sample_feed.json \\
      --pois B001A0LXYZ,B002B1MNPQ --transport driving
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv

load_dotenv()

from domain import IRFSessionState, RecommendationFeed
from domain.itinerary import BuildItineraryRequest
from graph.session_manager import SessionManager
from recsys.itinerary_errors import ItineraryPlannerError
from recsys.itinerary_planner import ItineraryPlanner


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a weekend itinerary from feed POIs")
    parser.add_argument("--session-id", default="cli-itinerary", help="Session id to use/store")
    parser.add_argument(
        "--pois",
        required=True,
        help="Comma-separated POI ids selected from the feed",
    )
    parser.add_argument(
        "--feed",
        help="Optional feed JSON fixture/path (seeds session when no IRF feed exists)",
    )
    parser.add_argument(
        "--transport",
        choices=["walking", "driving", "transit"],
        default="walking",
        help="Commute mode between stops",
    )
    parser.add_argument("--day-start", default="09:30")
    parser.add_argument("--day-end", default="21:00")
    parser.add_argument(
        "--anchor-poi-id",
        default=None,
        help="Force this POI to be visited first",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON response instead of timeline text",
    )
    return parser.parse_args()


def _seed_session(manager: SessionManager, session_id: str, feed_path: Path) -> None:
    feed = RecommendationFeed.model_validate_json(feed_path.read_text(encoding="utf-8"))
    state = IRFSessionState.empty().with_feed(feed)
    manager.create_session(session_id)
    manager.save_irf_state(session_id, state)


def main() -> int:
    args = _parse_args()
    poi_ids = [part.strip() for part in args.pois.split(",") if part.strip()]
    if not poi_ids:
        print("ERROR: --pois must list at least one POI id", file=sys.stderr)
        return 1

    sessions_dir = _BACKEND / "sessions"
    manager = SessionManager()
    manager.initialize(sessions_dir)

    if args.feed:
        _seed_session(manager, args.session_id, Path(args.feed))
    elif not manager._read_file(args.session_id):
        fixture = _BACKEND / "domain" / "fixtures" / "sample_feed.json"
        if not fixture.exists():
            print(
                "ERROR: session has no feed; pass --feed or run recommend first",
                file=sys.stderr,
            )
            return 1
        _seed_session(manager, args.session_id, fixture)

    request = BuildItineraryRequest(
        session_id=args.session_id,
        poi_ids=poi_ids,
        transport_mode=args.transport,
        day_start=args.day_start,
        day_end=args.day_end,
        anchor_poi_id=args.anchor_poi_id,
    )

    planner = ItineraryPlanner(sessions=manager)
    try:
        response = planner.build(request)
    except ItineraryPlannerError as exc:
        print(f"ERROR [{exc.code}]: {exc.message}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(response.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        print(response.itinerary.to_timeline_context())
        if response.warnings:
            print("\nWarnings:")
            for warning in response.warnings:
                print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
