"""
CIVICHEAT Decision-Support Risk Score — Thresholds and Rules.

IMPORTANT DISCLAIMER:
These are application-defined configurable thresholds for decision-support purposes.
They are NOT medically validated, NOT official government standards,
and NOT legally authoritative risk indices.

All thresholds live here and nowhere else. Never duplicate them.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

RiskLevel = Literal["LOW", "MODERATE", "HIGH", "EXTREME"]


@dataclass(frozen=True)
class TemperatureThreshold:
    level: RiskLevel
    min_c: float        # inclusive lower bound (°C)
    max_c: float        # exclusive upper bound (float('inf') for open-ended)
    score_floor: int    # minimum risk score for this level
    score_ceiling: int  # maximum risk score for this level
    color_hex: str      # map visualization color


# ---------------------------------------------------------------------------
# Temperature classification thresholds (Celsius)
# These are DEMO/application assumptions — not official standards.
# ---------------------------------------------------------------------------
TEMPERATURE_THRESHOLDS: list[TemperatureThreshold] = [
    TemperatureThreshold(
        level="LOW",
        min_c=float("-inf"),
        max_c=30.0,
        score_floor=0,
        score_ceiling=24,
        color_hex="#60a5fa",   # blue-400
    ),
    TemperatureThreshold(
        level="MODERATE",
        min_c=30.0,
        max_c=35.0,
        score_floor=25,
        score_ceiling=49,
        color_hex="#fbbf24",   # amber-400
    ),
    TemperatureThreshold(
        level="HIGH",
        min_c=35.0,
        max_c=40.0,
        score_floor=50,
        score_ceiling=74,
        color_hex="#f97316",   # orange-500
    ),
    TemperatureThreshold(
        level="EXTREME",
        min_c=40.0,
        max_c=float("inf"),
        score_floor=75,
        score_ceiling=100,
        color_hex="#dc2626",   # red-600
    ),
]

# ---------------------------------------------------------------------------
# Score weight configuration
# All components sum to 1.0 when all are available.
# When persistence/exceedance are not available, temperature carries full weight.
# ---------------------------------------------------------------------------
SCORE_WEIGHTS = {
    "temperature": 1.0,         # always available
    "persistence": 0.0,         # not available from FortyGuard yet
    "exceedance": 0.0,          # not available from FortyGuard yet
}

# ---------------------------------------------------------------------------
# Spatial grouping
# ---------------------------------------------------------------------------
ZONE_GROUPING_DISTANCE_DEG = 0.01   # ~1.1 km at Phoenix latitude
MIN_ZONE_FEATURE_COUNT = 3          # minimum tiles to form a reportable zone
MAX_PRIORITY_ZONES = 10             # cap on how many zones to surface

# ---------------------------------------------------------------------------
# Government recommendation triggers
# ---------------------------------------------------------------------------
ACTION_TRIGGER_RISK_LEVELS: dict[RiskLevel, list[str]] = {
    "LOW": [
        "Monitor temperature conditions.",
        "No immediate government action required.",
    ],
    "MODERATE": [
        "Increase monitoring frequency.",
        "Review heat preparedness protocols.",
        "Consider proactive public information.",
    ],
    "HIGH": [
        "Increase monitoring in affected area.",
        "Consider issuing a localized public heat advisory.",
        "Review outdoor municipal worker scheduling.",
        "Ensure cooling resources are on standby.",
    ],
    "EXTREME": [
        "Consider activating designated cooling facilities.",
        "Review outdoor municipal work schedules immediately.",
        "Issue a localized public heat advisory.",
        "Prioritize emergency resource deployment to affected zones.",
        "Notify relevant government departments.",
        "Schedule reassessment within 60 minutes.",
    ],
}

SCORE_DISCLAIMER = (
    "CIVICHEAT Decision-Support Risk Score — "
    "Application-defined heuristic. Not a medically validated or "
    "legally authoritative risk index."
)
