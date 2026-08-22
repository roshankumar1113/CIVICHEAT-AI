"""
Heatmap API routes.
Frontend never talks to FortyGuard directly — all calls go through here.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.fortyguard.fortyguard_client import (
    FortyGuardAPIError,
    FortyGuardTimeoutError,
)
from app.services.fortyguard.fortyguard_models import HeatIntelligence
from app.services.fortyguard.fortyguard_service import get_fortyguard_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class HeatmapAnalyzeRequest(BaseModel):
    city: str = Field("Phoenix, AZ", description="Human-readable city name for display")
    date: str = Field("2025-08-01", description="ISO date: YYYY-MM-DD")
    # Optional: custom polygon. If omitted, uses the city default.
    polygon_coordinates: list[list[list[float]]] | None = Field(
        None,
        description="GeoJSON polygon coordinates. If omitted, uses city default.",
    )
    demo_mode: bool = Field(
        False,
        description="Force DEMO mode — skip FortyGuard API and return cached data.",
    )


class HeatmapAnalyzeResponse(BaseModel):
    success: bool
    intelligence: HeatIntelligence
    data_mode: str
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/heatmap",
    response_model=HeatmapAnalyzeResponse,
    tags=["FortyGuard"],
    summary="Request heat intelligence for a city/polygon",
)
async def analyze_heatmap(request: HeatmapAnalyzeRequest) -> HeatmapAnalyzeResponse:
    """
    Submit a heatmap request to FortyGuard and return heat intelligence.

    - Submits POST /v1/heatmap to FortyGuard
    - Polls GET /v1/status/{activity_id} until completed
    - Returns parsed heat intelligence with GeoJSON tile data

    If `demo_mode=true` or FortyGuard is not configured, returns sample data.
    """
    service = get_fortyguard_service()

    if request.demo_mode or not service.is_configured():
        from app.services.fortyguard.fortyguard_parser import build_demo_intelligence
        intelligence = build_demo_intelligence(city=request.city, date=request.date)
        return HeatmapAnalyzeResponse(
            success=True,
            intelligence=intelligence,
            data_mode="DEMO",
            message="Demo mode — using sample FortyGuard data",
        )

    # Build optional custom polygon
    polygon = None
    if request.polygon_coordinates:
        from app.services.fortyguard.fortyguard_models import GeoJSONPolygon
        polygon = GeoJSONPolygon(
            type="Polygon",
            coordinates=request.polygon_coordinates,
        )

    try:
        logger.info(
            "Heatmap route: requesting intelligence | city=%s | date=%s",
            request.city,
            request.date,
        )
        intelligence = await service.get_heat_intelligence(
            city=request.city,
            date=request.date,
            polygon=polygon,
            use_demo_fallback=True,
        )
        return HeatmapAnalyzeResponse(
            success=True,
            intelligence=intelligence,
            data_mode=intelligence.data_mode,
            message=(
                "Live FortyGuard data retrieved successfully"
                if intelligence.data_mode == "LIVE"
                else "FortyGuard unavailable — using demo fallback"
            ),
        )

    except FortyGuardTimeoutError as exc:
        logger.error("Heatmap timeout: %s", exc)
        raise HTTPException(
            status_code=504,
            detail={"error": "FortyGuard request timed out", "message": str(exc)},
        )
    except FortyGuardAPIError as exc:
        logger.error("FortyGuard API error: %s", exc)
        raise HTTPException(
            status_code=502,
            detail={
                "error": "FortyGuard API error",
                "message": exc.message,
                "code": exc.status_code,
            },
        )
    except Exception as exc:
        logger.exception("Unexpected error in heatmap route")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal error", "message": "An unexpected error occurred"},
        )
