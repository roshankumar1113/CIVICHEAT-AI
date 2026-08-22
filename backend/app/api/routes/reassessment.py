"""
CIVICHEAT HeatWatch Reassessment endpoint.
POST /api/reassessment/run

Pipeline:
1. Run full FortyGuard → Risk → Priority analysis
2. Build snapshot
3. Compare with previous snapshot (if any)
4. If meaningful change → invoke Nemotron for updated recommendation
5. If no change → return monitoring status without Nemotron call
6. Save new snapshot to in-memory store
"""
from __future__ import annotations
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.fortyguard.fortyguard_client import FortyGuardAPIError, FortyGuardTimeoutError
from app.services.fortyguard.fortyguard_parser import build_demo_intelligence
from app.services.fortyguard.fortyguard_service import get_fortyguard_service
from app.services.heat_risk.risk_engine import run_risk_analysis
from app.services.nemotron.exceptions import (
    NemotronMalformedResponseError,
    NemotronTimeoutError,
    NemotronUnavailableError,
)
from app.services.nemotron.nemotron_agent import build_fallback_decision, run_agent
from app.services.nemotron.nemotron_client import NemotronClient
from app.services.nemotron.nemotron_prompts import REASSESSMENT_SYSTEM_PROMPT
from app.services.priority.priority_engine import run_priority_analysis
from app.services.reassessment.comparison_engine import compare_snapshots
from app.services.reassessment.comparison_models import (
    ChangeThresholds,
    ReassessmentResponse,
    ReassessmentStatus,
)
from app.services.reassessment.reassessment_service import (
    build_snapshot,
    get_analysis_store,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class ReassessmentRequest(BaseModel):
    city: str = Field("Phoenix, AZ")
    date: str = Field("2025-08-01")
    demo_mode: bool = Field(False)
    invoke_nemotron_on_change: bool = Field(
        True,
        description="If True, invoke Nemotron when meaningful change is detected.",
    )


@router.post(
    "/reassessment/run",
    response_model=ReassessmentResponse,
    tags=["HeatWatch"],
    summary="Run a CIVICHEAT reassessment and compare with previous analysis",
)
async def run_reassessment(request: ReassessmentRequest) -> ReassessmentResponse:
    """
    CIVICHEAT HeatWatch reassessment pipeline:

    1. Fetch fresh FortyGuard temperature intelligence
    2. Run Risk Engine + Priority Zone analysis
    3. Build a compact snapshot
    4. Compare with previous snapshot (in-memory store)
    5. If meaningful change detected → invoke Nemotron for updated plan
    6. If no meaningful change → return monitoring status (no Nemotron call)
    7. Save new snapshot

    All thresholds are application-defined (labeled CIVICHEAT reassessment rules).
    Not official emergency thresholds.
    """
    store = get_analysis_store()
    service = get_fortyguard_service()

    # ── Step 1: Fresh analysis ─────────────────────────────────────────────
    try:
        if request.demo_mode or not service.is_configured():
            intel = build_demo_intelligence(city=request.city, date=request.date)
        else:
            intel = await service.get_heat_intelligence(
                city=request.city, date=request.date, use_demo_fallback=True
            )

        risk_result = run_risk_analysis(intel)
        priority_result = run_priority_analysis(risk_result)

    except FortyGuardTimeoutError as exc:
        raise HTTPException(status_code=504, detail={"error": "FortyGuard timeout", "message": str(exc)})
    except FortyGuardAPIError as exc:
        raise HTTPException(status_code=502, detail={"error": "FortyGuard error", "message": exc.message})
    except Exception as exc:
        logger.exception("Reassessment: analysis pipeline failed")
        raise HTTPException(status_code=500, detail={"error": "Analysis failed", "message": "An unexpected error occurred"})

    # ── Step 2: Build + compare snapshots ────────────────────────────────
    current_snapshot = build_snapshot(priority_result)
    previous_snapshot = store.get_latest(request.city)

    thresholds = ChangeThresholds()

    if previous_snapshot is None:
        # First analysis — no comparison possible, just save and return
        store.save(current_snapshot)
        logger.info("Reassessment: first analysis for city=%s — no comparison", request.city)

        # Build a trivial "no change" comparison against self
        comparison = compare_snapshots(current_snapshot, current_snapshot, thresholds)
        comparison.change_reasons = []
        comparison.meaningful_change = False

        return ReassessmentResponse(
            success=True,
            data_mode=priority_result.data_mode,
            status=ReassessmentStatus(
                status="NO_SIGNIFICANT_CHANGE",
                message="First analysis stored. No previous data to compare.",
            ),
            comparison=comparison,
            previous_snapshot=None,
            current_snapshot=current_snapshot,
        )

    comparison = compare_snapshots(previous_snapshot, current_snapshot, thresholds)
    logger.info(
        "Reassessment: meaningful=%s | score_delta=%+d | reasons=%d",
        comparison.meaningful_change,
        comparison.risk_score_change,
        len(comparison.change_reasons),
    )

    # ── Step 3: Nemotron reassessment (only on meaningful change) ─────────
    nemotron_decision: dict[str, Any] | None = None
    nemotron_fallback = False
    tools_used: list[str] = []

    if comparison.meaningful_change and request.invoke_nemotron_on_change:
        # Build enriched context including comparison data
        ctx = dict(priority_result.agent_context)
        ctx["data_limitations"] = priority_result.data_limitations
        ctx["reassessment_comparison"] = {
            "previous_risk_score": comparison.previous_risk_score,
            "current_risk_score": comparison.current_risk_score,
            "risk_score_change": comparison.risk_score_change,
            "previous_risk_level": comparison.previous_risk_level,
            "current_risk_level": comparison.current_risk_level,
            "mean_temperature_change_c": comparison.mean_temperature_change_c,
            "previous_zone_count": comparison.previous_zone_count,
            "current_zone_count": comparison.current_zone_count,
            "change_reasons": comparison.change_reasons,
            "meaningful_change": comparison.meaningful_change,
        }

        prompt = (
            f"A reassessment has been triggered for {request.city}. "
            f"The risk score changed by {comparison.risk_score_change:+d} points "
            f"({comparison.previous_risk_level} → {comparison.current_risk_level}). "
            f"Determine whether the government response plan should be updated."
        )

        if NemotronClient().is_configured():
            try:
                decision, tools_used = await run_agent(
                    prompt, ctx,
                    system_prompt=REASSESSMENT_SYSTEM_PROMPT,
                )
                nemotron_decision = decision.model_dump()
                logger.info("Reassessment: Nemotron decision | risk=%s | tools=%s", decision.risk_level, tools_used)
            except (NemotronTimeoutError, NemotronUnavailableError, NemotronMalformedResponseError) as exc:
                logger.warning("Reassessment: Nemotron fallback | %s", exc)
                fallback = build_fallback_decision(ctx)
                nemotron_decision = fallback.model_dump()
                nemotron_fallback = True
                tools_used = ["get_current_heat_analysis", "compare_previous_analysis"]
        else:
            fallback = build_fallback_decision(ctx)
            nemotron_decision = fallback.model_dump()
            nemotron_fallback = True
            tools_used = ["get_current_heat_analysis", "compare_previous_analysis"]

    # ── Step 4: Save and return ───────────────────────────────────────────
    store.save(current_snapshot)

    status_str: str = "SIGNIFICANT_CHANGE" if comparison.meaningful_change else "NO_SIGNIFICANT_CHANGE"
    if comparison.meaningful_change:
        reason_summary = "; ".join(comparison.change_reasons[:2])
        message = f"Significant change detected: {reason_summary}"
    else:
        message = (
            f"No significant change detected. "
            f"Risk: {comparison.current_risk_score}/100 "
            f"(Δ{comparison.risk_score_change:+d}). Continue monitoring."
        )

    return ReassessmentResponse(
        success=True,
        data_mode=priority_result.data_mode,
        status=ReassessmentStatus(status=status_str, message=message),  # type: ignore[arg-type]
        comparison=comparison,
        previous_snapshot=previous_snapshot,
        current_snapshot=current_snapshot,
        nemotron_decision=nemotron_decision,
        nemotron_fallback=nemotron_fallback,
        tools_used=tools_used,
    )


@router.get(
    "/reassessment/history",
    tags=["HeatWatch"],
    summary="Return the latest stored snapshot for a city",
)
async def get_history(city: str = "Phoenix, AZ") -> dict:
    store = get_analysis_store()
    latest = store.get_latest(city)
    previous = store.get_previous(city)
    return {
        "city": city,
        "stored_analyses": store.count(city),
        "latest": latest.model_dump() if latest else None,
        "previous": previous.model_dump() if previous else None,
    }
