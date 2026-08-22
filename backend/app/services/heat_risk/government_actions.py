"""
Deterministic government intervention recommendations.

IMPORTANT:
- This system does NOT automatically contact government agencies.
- It does NOT trigger emergency systems.
- It is a DECISION-SUPPORT tool only.
- All recommendations are for human review and decision.
"""
from __future__ import annotations
from app.services.heat_risk.risk_rules import ACTION_TRIGGER_RISK_LEVELS, RiskLevel


def get_recommended_actions(risk_level: RiskLevel, context: str = "") -> list[str]:
    """Return deterministic government action recommendations for a risk level."""
    base = ACTION_TRIGGER_RISK_LEVELS.get(risk_level, [])
    return list(base)


def get_action_rationale(risk_level: RiskLevel, temp_c: float) -> str:
    """Return a concise evidence-based rationale string."""
    rationale_map = {
        "LOW": (
            f"Temperature {temp_c:.1f}°C is below action thresholds. "
            "Routine monitoring is sufficient."
        ),
        "MODERATE": (
            f"Temperature {temp_c:.1f}°C is elevated. "
            "Preparedness review is recommended."
        ),
        "HIGH": (
            f"Temperature {temp_c:.1f}°C is significantly elevated. "
            "Localized government response should be considered."
        ),
        "EXTREME": (
            f"Temperature {temp_c:.1f}°C is critically elevated. "
            "Immediate government response review is recommended."
        ),
    }
    return rationale_map.get(risk_level, "")
