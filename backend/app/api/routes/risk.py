"""
Risk analysis API routes.
POST /api/risk/analyze  — accepts FortyGuard heat intelligence, returns risk analysis
"""
from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException
from app.services.fortyguard.fortyguard_models import HeatIntelligence
from app.services.heat_risk.risk_engine import run_risk_analysis
from app.services.heat_risk.risk_models import RiskAnalysisResult

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/risk/analyze",
    response_model=RiskAnalysisResult,
    tags=["Risk Engine"],
    summary="Analyze heat risk from FortyGuard intelligence",
)
async def analyze_risk(intelligence: HeatIntelligence) -> RiskAnalysisResult:
    """
    Accept a HeatIntelligence object (from FortyGuard) and return
    a full CIVICHEAT Decision-Support Risk Analysis.

    Risk scores are 0–100 (CIVICHEAT heuristic — not a medical index).
    """
    try:
        result = run_risk_analysis(intelligence)
        logger.info(
            "Risk route: analysis complete | city=%s | overall=%s | score=%d",
            result.city,
            result.summary.overall_risk_level,
            result.summary.overall_risk_score,
        )
        return result
    except Exception as exc:
        logger.exception("Risk analysis failed")
        raise HTTPException(
            status_code=500,
            detail={"error": "Risk analysis failed", "message": str(exc)},
        )
