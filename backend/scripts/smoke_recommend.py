#!/usr/bin/env python3
"""End-to-end smoke test for POST /api/recommend (Day 4.8)."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))

BASE_URL = "http://127.0.0.1:8002"
SESSION_ID = "smoke-recommend"
OUTPUT_PATH = _BASE / "sessions" / "smoke-recommend.json"


def _post_recommend(command: str, *, stream: bool = False) -> dict:
    payload = json.dumps(
        {"command": command, "session_id": SESSION_ID, "stream": stream},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/recommend",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def _wait_for_server(timeout_s: float = 60.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/", timeout=2) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)
    raise RuntimeError(f"backend not reachable at {BASE_URL}")


def main() -> int:
    _wait_for_server()

    round1 = _post_recommend("上海周末想找个文艺的地方，不要太远")
    if round1.get("error"):
        print("round1 error:", round1["error"], file=sys.stderr)
        return 1
    assert round1.get("feed"), "round1 missing feed"
    assert round1.get("round") == 1, f"expected round 1, got {round1.get('round')}"
    print(f"round1 OK: {len(round1['feed']['items'])} items")

    round2 = _post_recommend("换几家咖啡馆，人均别太贵")
    if round2.get("error"):
        print("round2 error:", round2["error"], file=sys.stderr)
        return 1
    assert round2.get("feed"), "round2 missing feed"
    assert round2.get("round") == 2, f"expected round 2, got {round2.get('round')}"
    print(f"round2 OK: {len(round2['feed']['items'])} items")

    session_path = _BASE / "sessions" / f"{SESSION_ID}.json"
    session_irf = {}
    if session_path.exists():
        session_data = json.loads(session_path.read_text(encoding="utf-8"))
        session_irf = session_data.get("irf", {})

    artifact = {
        "session_id": SESSION_ID,
        "round1": round1,
        "round2": round2,
        "session_irf": session_irf,
    }
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"saved {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
