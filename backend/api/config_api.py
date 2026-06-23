"""GET/PUT /api/config/* — RAG mode toggle + API Key management."""

import os
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from config import get_rag_mode, set_rag_mode
from tools.amap_keys import AMAP_WEB_SERVICE_LEGACY_ENV, get_amap_web_service_key

router = APIRouter()

# ── RAG mode ──────────────────────────────────────────

class RagModeRequest(BaseModel):
    enabled: bool


@router.get("/config/rag-mode")
async def get_rag_mode_endpoint():
    return {"rag_mode": get_rag_mode()}


@router.put("/config/rag-mode")
async def set_rag_mode_endpoint(request: RagModeRequest):
    set_rag_mode(request.enabled)
    return {"rag_mode": request.enabled}


# ── API Key management ────────────────────────────────

MANAGED_KEYS = [
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "TAVILY_API_KEY",
    "AMAP_WEB_SERVICE_KEY",
]
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _parse_env_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    return stripped.split("=", 1)[0].strip()


def _build_key_line_map(lines: list[str]) -> Dict[str, int]:
    """Map managed env keys to line indices; legacy AMAP_API_KEY maps to Web Service."""
    key_line_map: Dict[str, int] = {}
    for index, line in enumerate(lines):
        key = _parse_env_key(line)
        if not key:
            continue
        if key in MANAGED_KEYS:
            key_line_map[key] = index
        elif key == AMAP_WEB_SERVICE_LEGACY_ENV:
            key_line_map["AMAP_WEB_SERVICE_KEY"] = index
    return key_line_map


def _mask_value(key_name: str, value: str) -> str:
    """Mask API key values, leave URLs unmasked."""
    if not value:
        return ""
    if key_name.endswith("_URL"):
        return value
    if len(value) <= 8:
        return "****"
    return value[:3] + "****" + value[-4:]


@router.get("/config/api-keys")
async def get_api_keys():
    """Return masked API keys from environment."""
    keys: Dict[str, str] = {}
    for key_name in MANAGED_KEYS:
        if key_name == "AMAP_WEB_SERVICE_KEY":
            val = get_amap_web_service_key() or ""
        else:
            val = os.getenv(key_name, "")
        keys[key_name] = _mask_value(key_name, val)
    return keys


class ApiKeysRequest(BaseModel):
    keys: Dict[str, str]


@router.put("/config/api-keys")
async def set_api_keys(request: ApiKeysRequest):
    """Update .env file with new keys (only non-empty values)."""
    # Read existing .env content
    existing_lines: list[str] = []
    if ENV_PATH.exists():
        existing_lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    key_line_map = _build_key_line_map(existing_lines)

    # Update or append
    for key_name, new_value in request.keys.items():
        if key_name not in MANAGED_KEYS:
            continue
        if not new_value or "****" in new_value:
            # Skip empty or masked (unchanged) values
            continue

        env_line = f"{key_name}={new_value}"
        if key_name == "AMAP_WEB_SERVICE_KEY":
            # 迁移：移除旧 AMAP_API_KEY 行，统一使用 AMAP_WEB_SERVICE_KEY
            existing_lines = [
                line
                for line in existing_lines
                if _parse_env_key(line) != AMAP_WEB_SERVICE_LEGACY_ENV
            ]
            key_line_map = _build_key_line_map(existing_lines)
            os.environ.pop(AMAP_WEB_SERVICE_LEGACY_ENV, None)

        if key_name in key_line_map:
            existing_lines[key_line_map[key_name]] = env_line
        else:
            existing_lines.append(env_line)

        # Also update current process env
        os.environ[key_name] = new_value

    # Write back
    ENV_PATH.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")

    # Return masked keys
    result: Dict[str, str] = {}
    for key_name in MANAGED_KEYS:
        val = os.getenv(key_name, "")
        if key_name == "AMAP_WEB_SERVICE_KEY" and not val:
            val = get_amap_web_service_key() or ""
        result[key_name] = _mask_value(key_name, val)
    return result
