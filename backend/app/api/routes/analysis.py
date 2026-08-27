"""
Combined analysis endpoint: FortyGuard → Risk → Priority → structured response.
POST /api/heatmap/analyze
"""
from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.fortyguard.fortyguard_client import FortyGuardAPIError, FortyGuardTimeoutError
from app.services.fortyguard.fortyguard_parser import build_demo_intelligence
from app.services.fortyguard.fortyguard_service import get_fortyguard_service
from app.services.heat_risk.risk_engine import run_risk_analysis
from app.services.priority.priority_engine import run_priority_analysis
from app.services.priority.priority_models import PriorityAnalysisResult
from app.services.reassessment.reassessment_service import build_snapshot, get_analysis_store

logger = logging.getLogger(__name__)
router = APIRouter()


class AnalyzeRequest(BaseModel):
    city: str = Field("Phoenix, AZ", description="City name for display")
    date: str = Field("2025-08-01", description="ISO date: YYYY-MM-DD")
    demo_mode: bool = Field(False, description="Use demo data instead of live FortyGuard")


class AnalyzeResponse(BaseModel):
    success: bool
    data_mode: str
    message: str
    result: PriorityAnalysisResult
    # Raw FortyGuard tile FeatureCollection for the map's temperature layer.
    # Deliberately kept OUT of result.agent_context so the Nemotron agent is
    # never handed the full per-tile feature set.
    tile_geojson: dict | None = None
    tile_count: int = 0


@router.post(
    "/heatmap/analyze",
    response_model=AnalyzeResponse,
    tags=["Analysis"],
    summary="Full pipeline: FortyGuard → Risk Engine → Priority Zones",
)
async def full_analysis(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Full CIVICHEAT analysis pipeline:
    1. Fetch FortyGuard heat intelligence
    2. Run CIVICHEAT risk engine on all features
    3. Cluster into priority zones
    4. Generate government action recommendations
    5. Return structured result ready for the dashboard

    This endpoint drives the main dashboard.
    """
    service = get_fortyguard_service()

    try:
        if request.demo_mode or not service.is_configured():
            intelligence = build_demo_intelligence(city=request.city, date=request.date)
            message = "Demo mode — using sample FortyGuard data"
        else:
            intelligence = await service.get_heat_intelligence(
                city=request.city,
                date=request.date,
                use_demo_fallback=True,
            )
            message = (
                "Live FortyGuard data"
                if intelligence.data_mode == "LIVE"
                else "FortyGuard unavailable — demo fallback"
            )

        risk_result = run_risk_analysis(intelligence)
        priority_result = run_priority_analysis(risk_result)

        logger.info(
            "Analysis route: complete | city=%s | zones=%d | highest=%s",
            request.city,
            len(priority_result.priority_zones),
            priority_result.highest_risk_level,
        )

        # Auto-save snapshot so reassessment has prior data to compare
        snapshot = build_snapshot(priority_result)
        get_analysis_store().save(snapshot)

        return AnalyzeResponse(
            success=True,
            data_mode=priority_result.data_mode,
            message=message,
            result=priority_result,
            tile_geojson=intelligence.geojson,
            tile_count=intelligence.tile_count,
        )

    except FortyGuardTimeoutError as exc:
        raise HTTPException(status_code=504, detail={"error": "FortyGuard timeout", "message": str(exc)})
    except FortyGuardAPIError as exc:
        raise HTTPException(status_code=502, detail={"error": "FortyGuard error", "message": exc.message})
    except Exception as exc:
        logger.exception("Analysis pipeline failed")
        raise HTTPException(status_code=500, detail={"error": "Analysis failed", "message": "An unexpected error occurred"})
