"""GET/PUT /api/config/* — RAG mode toggle + API Key management."""

import os
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from config import get_rag_mode, set_rag_mode

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

MANAGED_KEYS = ["DEEPSEEK_API_KEY", "OPENAI_API_KEY", "OPENAI_BASE_URL", "TAVILY_API_KEY", "AMAP_API_KEY"]
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


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

    # Build a map of key -> line index for existing entries
    key_line_map: Dict[str, int] = {}
    for i, line in enumerate(existing_lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in MANAGED_KEYS:
                key_line_map[k] = i

    # Update or append
    for key_name, new_value in request.keys.items():
        if key_name not in MANAGED_KEYS:
            continue
        if not new_value or "****" in new_value:
            # Skip empty or masked (unchanged) values
            continue

        env_line = f"{key_name}={new_value}"
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
        result[key_name] = _mask_value(key_name, val)
    return result
