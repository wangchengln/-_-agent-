"""Amap API key resolution — Web 服务 vs JS API 分离（Day 6.7）."""

from __future__ import annotations

import os

# Web 服务 REST API（POI / 天气 / 路径 / 静态图等）
AMAP_WEB_SERVICE_ENV = "AMAP_WEB_SERVICE_KEY"
# 旧版变量名，向后兼容
AMAP_WEB_SERVICE_LEGACY_ENV = "AMAP_API_KEY"


def get_amap_web_service_key() -> str | None:
    """Return the Web Service API key for backend REST calls."""
    raw = os.getenv(AMAP_WEB_SERVICE_ENV) or os.getenv(AMAP_WEB_SERVICE_LEGACY_ENV)
    if raw and raw.strip():
        return raw.strip()
    return None
