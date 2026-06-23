#!/usr/bin/env python3
"""Tests for Amap key resolution (Web 服务 vs legacy env)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from tools.amap_keys import (
    AMAP_WEB_SERVICE_ENV,
    AMAP_WEB_SERVICE_LEGACY_ENV,
    get_amap_web_service_key,
)


class TestAmapKeys(unittest.TestCase):
    def test_prefers_web_service_env(self) -> None:
        env = {
            AMAP_WEB_SERVICE_ENV: "web-key",
            AMAP_WEB_SERVICE_LEGACY_ENV: "legacy-key",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(get_amap_web_service_key(), "web-key")

    def test_falls_back_to_legacy_env(self) -> None:
        with patch.dict(os.environ, {AMAP_WEB_SERVICE_LEGACY_ENV: "legacy-key"}, clear=True):
            self.assertEqual(get_amap_web_service_key(), "legacy-key")

    def test_missing_returns_none(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(get_amap_web_service_key())


if __name__ == "__main__":
    unittest.main()
