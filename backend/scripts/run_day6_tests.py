#!/usr/bin/env python3
"""Run Day 6 backend test suite (Day 6.8).

Usage (conda langchain-test):
  cd backend
  set PYTHONPATH=.
  python scripts/run_day6_tests.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent

DAY6_TESTS = [
    "tests/test_amap_keys.py",
    "tests/test_recommend_types_contract.py",
    "tests/test_itinerary_contract.py",
    "tests/test_weather_hook.py",
    "tests/test_itinerary_schemas.py",
    "tests/test_itinerary_planner.py",
    "tests/test_itinerary_api.py",
    "tests/test_day6_integration.py",
]


def main() -> int:
    env = {**os.environ, "PYTHONPATH": str(BACKEND)}
    cmd = [sys.executable, "-m", "pytest", *DAY6_TESTS, "-q", "--tb=short"]
    print("Running Day 6 tests:", " ".join(DAY6_TESTS))
    result = subprocess.run(cmd, cwd=BACKEND, env=env)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
