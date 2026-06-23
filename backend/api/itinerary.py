"""POST /api/itinerary — build a weekend itinerary from selected feed POIs."""

from __future__ import annotations

import asyncio
import traceback

from fastapi import APIRouter, HTTPException

from domain.itinerary import BuildItineraryRequest, BuildItineraryResponse
from recsys.itinerary_errors import ItineraryPlannerError, itinerary_error_message
from recsys.itinerary_planner import ItineraryPlanner, itinerary_planner

router = APIRouter()


async def run_build_itinerary(
    request: BuildItineraryRequest,
    planner: ItineraryPlanner | None = None,
) -> BuildItineraryResponse:
    """Core handler — inject ``planner`` in tests; production uses ``itinerary_planner``."""
    runner = planner or itinerary_planner
    try:
        return await asyncio.to_thread(runner.build, request)
    except ItineraryPlannerError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "code": "internal_error",
                "message": itinerary_error_message("internal_error", detail=str(exc)),
            },
        ) from exc


@router.post("/itinerary", response_model=BuildItineraryResponse)
async def build_itinerary(request: BuildItineraryRequest) -> BuildItineraryResponse:
    """Plan a multi-stop weekend timeline from POIs in the current session feed."""
    return await run_build_itinerary(request)
