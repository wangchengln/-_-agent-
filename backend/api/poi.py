"""GET /api/poi/{poi_id} — enriched POI detail with Amap reviews."""

from __future__ import annotations

import asyncio
import traceback

from fastapi import APIRouter, HTTPException, Query

from domain.poi_detail import PoiDetail
from graph.session_manager import session_manager
from recsys.poi_detail_service import PoiDetailService, poi_detail_service
from tools.amap_client import AmapApiError, AmapClientError

router = APIRouter()


async def run_get_poi_detail(
    session_id: str,
    poi_id: str,
    service: PoiDetailService | None = None,
) -> PoiDetail:
    runner = service or poi_detail_service
    try:
        return await asyncio.to_thread(runner.get_detail, session_id, poi_id)
    except AmapClientError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "amap_error", "message": str(exc)},
        ) from exc
    except AmapApiError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "poi_not_found", "message": str(exc)},
        ) from exc
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={"code": "internal_error", "message": str(exc)},
        ) from exc


@router.get("/poi/{poi_id}", response_model=PoiDetail)
async def get_poi_detail(
    poi_id: str,
    session_id: str = Query(..., min_length=1),
) -> PoiDetail:
    """Return POI detail merged from session feed cache and live Amap APIs."""
    if not session_manager._read_file(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return await run_get_poi_detail(session_id, poi_id)
