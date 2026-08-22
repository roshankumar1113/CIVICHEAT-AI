"""
CIVICHEAT Nemotron Agent API routes.

POST /api/agent/analyze        — main "Ask CIVICHEAT" endpoint
POST /api/agent/action-plan    — structured action plan for a zone
POST /api/agent/public-advisory — AI-generated advisory draft
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.fortyguard.fortyguard_parser import build_demo_intelligence
from app.services.fortyguard.fortyguard_service import get_fortyguard_service
from app.services.heat_risk.government_actions import get_recommended_actions
from app.services.heat_risk.risk_engine import run_risk_analysis
from app.services.nemotron.exceptions import (
    NemotronMalformedResponseError,
    NemotronTimeoutError,
    NemotronUnavailableError,
)
from app.services.nemotron.nemotron_agent import (
    CIVICHEAT_TOOLS,
    AgentTools,
    build_fallback_decision,
    run_agent,
)
from app.services.nemotron.nemotron_client import NemotronClient
from app.services.nemotron.nemotron_models import (
    ActionPlanResponse,
    AgentResponse,
    PublicAdvisoryResponse,
    RecommendedAction,
    ReassessmentPlan,
)
from app.services.nemotron.nemotron_prompts import (
    ACTION_PLAN_SYSTEM_PROMPT,
    ADVISORY_SYSTEM_PROMPT,
    JSON_CORRECTION_PROMPT,
)
from app.services.priority.priority_engine import run_priority_analysis

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Shared helper: fetch + analyse (with demo fallback)
# ---------------------------------------------------------------------------

async def _get_analysis_context(city: str, date: str, demo_mode: bool) -> dict[str, Any]:
    """Run the full FortyGuard → Risk → Priority pipeline and return agent_context."""
    service = get_fortyguard_service()
    if demo_mode or not service.is_configured():
        intel = build_demo_intelligence(city=city, date=date)
    else:
        intel = await service.get_heat_intelligence(city=city, date=date, use_demo_fallback=True)

    risk_result = run_risk_analysis(intel)
    priority_result = run_priority_analysis(risk_result)

    # agent_context already contains everything the agent needs
    ctx = dict(priority_result.agent_context)
    ctx["data_limitations"] = priority_result.data_limitations
    return ctx


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class AgentAnalyzeRequest(BaseModel):
    message: str = Field(
        "What should the government do right now?",
        description="Natural language question for the agent",
    )
    city: str = Field("Phoenix, AZ")
    date: str = Field("2025-08-01")
    demo_mode: bool = Field(False)


class ActionPlanRequest(BaseModel):
    zone_id: str = Field(..., description="Zone ID, e.g. ZONE-001")
    city: str = Field("Phoenix, AZ")
    date: str = Field("2025-08-01")
    demo_mode: bool = Field(False)


class AdvisoryRequest(BaseModel):
    city: str = Field("Phoenix, AZ")
    date: str = Field("2025-08-01")
    demo_mode: bool = Field(False)


# ---------------------------------------------------------------------------
# POST /api/agent/analyze
# ---------------------------------------------------------------------------

@router.post(
    "/agent/analyze",
    response_model=AgentResponse,
    tags=["Agent"],
    summary="Ask CIVICHEAT — agentic heat-response decision support",
)
async def agent_analyze(request: AgentAnalyzeRequest) -> AgentResponse:
    """
    The core Track 6 endpoint.

    The Nemotron agent:
    1. Calls get_current_heat_analysis()
    2. Calls get_priority_zones()
    3. Calls inspect_zone() on the top zone
    4. Optionally calls calculate_intervention_priority()
    5. Produces a structured AgentDecision

    If Nemotron is unavailable, falls back to deterministic Phase 3 engine
    (clearly labeled FALLBACK_MODE in the response).
    """
    settings_ok = NemotronClient().is_configured()
    ctx = await _get_analysis_context(request.city, request.date, request.demo_mode)

    if not settings_ok:
        logger.warning("Agent: Nemotron not configured — using fallback")
        decision = build_fallback_decision(ctx)
        return AgentResponse(
            agent={"provider": "CIVICHEAT Deterministic Fallback", "model": "phase3-engine", "status": "fallback"},
            decision=decision,
            tools_used=["get_current_heat_analysis", "get_priority_zones"],
            fallback_mode=True,
            fallback_reason="Nemotron not configured.",
        )

    try:
        decision, tools_used = await run_agent(request.message, ctx)
        logger.info(
            "Agent: decision complete | zone=%s | risk=%s | tools=%s",
            decision.priority_zone,
            decision.risk_level,
            tools_used,
        )
        return AgentResponse(
            agent={"provider": "NVIDIA Nemotron", "model": NemotronClient()._model, "status": "completed"},
            decision=decision,
            tools_used=tools_used,
            fallback_mode=False,
        )

    except NemotronTimeoutError as exc:
        logger.warning("Agent: Nemotron timeout — fallback | %s", exc)
        decision = build_fallback_decision(ctx)
        return AgentResponse(
            agent={"provider": "CIVICHEAT Fallback", "model": "phase3-engine", "status": "timeout_fallback"},
            decision=decision,
            tools_used=["get_current_heat_analysis", "get_priority_zones"],
            fallback_mode=True,
            fallback_reason=f"Nemotron timed out: {exc}",
        )

    except (NemotronUnavailableError, NemotronMalformedResponseError) as exc:
        logger.warning("Agent: Nemotron error — fallback | %s", exc)
        decision = build_fallback_decision(ctx)
        return AgentResponse(
            agent={"provider": "CIVICHEAT Fallback", "model": "phase3-engine", "status": "error_fallback"},
            decision=decision,
            tools_used=["get_current_heat_analysis", "get_priority_zones"],
            fallback_mode=True,
            fallback_reason=str(exc),
        )

    except Exception as exc:
        logger.exception("Agent: unexpected error")
        raise HTTPException(
            status_code=500,
            detail={"error": "Agent error", "message": "An unexpected error occurred"},
        )


# ---------------------------------------------------------------------------
# POST /api/agent/action-plan
# ---------------------------------------------------------------------------

@router.post(
    "/agent/action-plan",
    response_model=ActionPlanResponse,
    tags=["Agent"],
    summary="Generate a structured government action plan for a zone",
)
async def agent_action_plan(request: ActionPlanRequest) -> ActionPlanResponse:
    """
    Generate a zone-specific government action plan.
    The agent inspects the zone and produces a structured plan.
    Falls back to deterministic recommendations if Nemotron is unavailable.
    """
    ctx = await _get_analysis_context(request.city, request.date, request.demo_mode)
    tools_exec = AgentTools(ctx)

    # Get zone data for fallback and evidence
    zone_result = json.loads(tools_exec.execute("inspect_zone", {"zone_id": request.zone_id}))
    if "error" in zone_result:
        raise HTTPException(
            status_code=404,
            detail={"error": "Zone not found", "message": zone_result["error"]},
        )

    # Attempt Nemotron
    if NemotronClient().is_configured():
        try:
            prompt = (
                f"Generate a government action plan for zone {request.zone_id} "
                f"in {request.city} on {request.date}."
            )
            decision, _ = await run_agent(prompt, ctx, system_prompt=ACTION_PLAN_SYSTEM_PROMPT)

            risk_level = zone_result.get("risk_level", decision.risk_level)
            return ActionPlanResponse(
                incident_summary=decision.decision,
                priority=risk_level,  # type: ignore[arg-type]
                zone=request.zone_id,
                actions=decision.recommended_actions,
                evidence=decision.evidence,
                limitations=decision.limitations,
                reassessment=decision.reassessment,
                fallback_mode=False,
            )
        except (NemotronUnavailableError, NemotronTimeoutError, NemotronMalformedResponseError) as exc:
            logger.warning("Action plan: Nemotron fallback | %s", exc)

    # Deterministic fallback
    risk_level = zone_result.get("risk_level", "MODERATE")
    raw_actions = get_recommended_actions(risk_level)  # type: ignore[arg-type]
    actions = [
        RecommendedAction(
            action=a,
            reason=f"Based on {risk_level} risk classification.",
            urgency="HIGH" if risk_level in ("HIGH", "EXTREME") else "MEDIUM",
        )
        for a in raw_actions
    ]
    evidence = [
        f"Zone {request.zone_id}: {risk_level} risk",
        f"Mean temperature: {zone_result.get('temperature_mean_c', 0):.1f}°C",
        f"Peak temperature: {zone_result.get('temperature_max_c', 0):.1f}°C",
        f"CIVICHEAT risk score: {zone_result.get('risk_score', 0)}/100",
        f"Affected tiles: {zone_result.get('feature_count', 0)}",
    ]

    return ActionPlanResponse(
        incident_summary=(
            f"Zone {request.zone_id} in {request.city} shows {risk_level} risk conditions "
            f"with a mean temperature of {zone_result.get('temperature_mean_c', 0):.1f}°C."
        ),
        priority=risk_level,  # type: ignore[arg-type]
        zone=request.zone_id,
        actions=actions,
        evidence=evidence,
        limitations=ctx.get("data_limitations", []) + ["FALLBACK MODE: Nemotron unavailable."],
        reassessment=ReassessmentPlan(recommended=True, interval_minutes=60),
        fallback_mode=True,
    )


# ---------------------------------------------------------------------------
# POST /api/agent/public-advisory
# ---------------------------------------------------------------------------

@router.post(
    "/agent/public-advisory",
    response_model=PublicAdvisoryResponse,
    tags=["Agent"],
    summary="Generate a public heat advisory draft (requires official review)",
)
async def agent_public_advisory(request: AdvisoryRequest) -> PublicAdvisoryResponse:
    """
    Generate a draft public advisory. Clearly labeled as AI-generated draft
    requiring official review. Never makes medical claims.
    """
    ctx = await _get_analysis_context(request.city, request.date, request.demo_mode)
    temp = ctx.get("temperature_summary", {})
    risk = ctx.get("risk_summary", {})

    if NemotronClient().is_configured():
        try:
            prompt = (
                f"Generate a public heat advisory for {request.city} on {request.date}. "
                f"Current conditions: {risk.get('overall_level')} risk, "
                f"{temp.get('mean_c', 0):.1f}°C mean temperature."
            )
            decision, _ = await run_agent(prompt, ctx, system_prompt=ADVISORY_SYSTEM_PROMPT)
            return PublicAdvisoryResponse(
                title="HEAT ADVISORY — DRAFT",
                body=decision.decision,
                fallback_mode=False,
            )
        except (NemotronUnavailableError, NemotronTimeoutError, NemotronMalformedResponseError) as exc:
            logger.warning("Advisory: Nemotron fallback | %s", exc)

    # Deterministic fallback
    risk_level = risk.get("overall_level", "MODERATE")
    mean_c = temp.get("mean_c", 0)
    body = (
        f"Elevated temperatures have been detected in {request.city}. "
        f"Current conditions indicate {risk_level.lower()} heat risk conditions "
        f"with a mean temperature of {mean_c:.1f}°C. "
        f"Consider limiting prolonged outdoor activity during peak hours "
        f"and identifying available cooling resources in your area."
    )
    return PublicAdvisoryResponse(
        title="HEAT ADVISORY — DRAFT",
        body=body,
        fallback_mode=True,
    )
