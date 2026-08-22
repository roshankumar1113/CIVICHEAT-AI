"""
CIVICHEAT Heat Risk Engine.

Converts FortyGuard HeatIntelligence into a structured risk analysis.
All calculations are deterministic and traceable — no LLM, no random values.
"""
from __future__ import annotations

import logging
import math

from app.services.fortyguard.fortyguard_models import HeatIntelligence
from app.services.heat_risk.risk_models import (
    AnalysisSummary,
    FeatureRiskResult,
    RiskAnalysisResult,
    RiskLevel,
)
from app.services.heat_risk.risk_rules import (
    SCORE_DISCLAIMER,
    TEMPERATURE_THRESHOLDS,
    TemperatureThreshold,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core classification functions
# ---------------------------------------------------------------------------

def classify_temperature(temp_c: float) -> TemperatureThreshold:
    """Return the threshold bucket for a given temperature."""
    for threshold in reversed(TEMPERATURE_THRESHOLDS):
        if temp_c >= threshold.min_c:
            return threshold
    return TEMPERATURE_THRESHOLDS[0]


def calculate_temperature_score(temp_c: float) -> tuple[int, TemperatureThreshold]:
    """
    Map temperature to a 0–100 integer score within the classified band.

    Scoring is linear within each band:
      LOW      0°C–30°C    → 0–24
      MODERATE 30°C–35°C   → 25–49
      HIGH     35°C–40°C   → 50–74
      EXTREME  ≥40°C       → 75–100 (capped at 100)

    Returns (score, threshold).
    """
    threshold = classify_temperature(temp_c)

    floor = threshold.score_floor
    ceiling = threshold.score_ceiling

    if threshold.max_c == float("inf"):
        # EXTREME: linear from 40°C → 75 up to 50°C → 100, capped
        span_c = 10.0
        excess = temp_c - threshold.min_c
        fraction = min(excess / span_c, 1.0)
    else:
        band_width = threshold.max_c - threshold.min_c
        excess = temp_c - threshold.min_c
        fraction = excess / band_width if band_width > 0 else 0.0
        fraction = max(0.0, min(fraction, 1.0))

    score = floor + round(fraction * (ceiling - floor))
    score = max(0, min(100, score))
    return score, threshold


def score_to_risk_level(score: int) -> RiskLevel:
    for threshold in reversed(TEMPERATURE_THRESHOLDS):
        if score >= threshold.score_floor:
            return threshold.level
    return "LOW"


# ---------------------------------------------------------------------------
# Feature-level analysis
# ---------------------------------------------------------------------------

def analyze_feature(feature: dict) -> FeatureRiskResult:
    """
    Analyze a single FortyGuard GeoJSON feature.
    Uses average_temperature as the primary signal.
    """
    props = feature.get("properties", {})
    temp_c: float = props.get("average_temperature", 0.0)
    feature_id: str = str(feature.get("id", "unknown"))
    geometry: dict = feature.get("geometry", {})

    score, threshold = calculate_temperature_score(temp_c)

    reasons: list[str] = [
        f"Average temperature {temp_c:.1f}°C classified as {threshold.level}."
    ]

    return FeatureRiskResult(
        feature_id=feature_id,
        temperature_c=round(temp_c, 2),
        risk_level=threshold.level,
        risk_score=score,
        reasons=reasons,
        temperature_component=round(temp_c, 4),
        persistence_available=False,
        exceedance_available=False,
        geometry=geometry,
    )


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------

def run_risk_analysis(intelligence: HeatIntelligence) -> RiskAnalysisResult:
    """
    Run risk analysis across all FortyGuard features.
    Returns a structured RiskAnalysisResult ready for the priority engine.
    """
    features = intelligence.geojson.get("features", [])
    logger.info(
        "Risk engine: analyzing %d features | city=%s | date=%s",
        len(features),
        intelligence.city,
        intelligence.date,
    )

    feature_results: list[FeatureRiskResult] = [
        analyze_feature(f) for f in features
    ]

    # Aggregate counts
    counts: dict[RiskLevel, int] = {"LOW": 0, "MODERATE": 0, "HIGH": 0, "EXTREME": 0}
    for r in feature_results:
        counts[r.risk_level] += 1

    # Overall risk = highest level with at least one feature; fall back to mean
    if counts["EXTREME"] > 0:
        overall_level: RiskLevel = "EXTREME"
    elif counts["HIGH"] > 0:
        overall_level = "HIGH"
    elif counts["MODERATE"] > 0:
        overall_level = "MODERATE"
    else:
        overall_level = "LOW"

    # Overall score = mean of all feature scores
    if feature_results:
        overall_score = round(sum(r.risk_score for r in feature_results) / len(feature_results))
    else:
        overall_score = 0

    summary = AnalysisSummary(
        total_features=len(feature_results),
        mean_temperature_c=round(intelligence.mean_temperature, 2),
        max_temperature_c=round(intelligence.max_temperature, 2),
        min_temperature_c=round(intelligence.min_temperature, 2),
        low_risk_features=counts["LOW"],
        moderate_risk_features=counts["MODERATE"],
        high_risk_features=counts["HIGH"],
        extreme_risk_features=counts["EXTREME"],
        overall_risk_level=overall_level,
        overall_risk_score=overall_score,
        persistence_available=False,
        exceedance_available=False,
        score_disclaimer=SCORE_DISCLAIMER,
    )

    # Build Nemotron-ready context (used in Phase 4)
    agent_context = {
        "city": intelligence.city,
        "date": intelligence.date,
        "data_mode": intelligence.data_mode,
        "temperature_summary": {
            "mean_c": intelligence.mean_temperature,
            "min_c": intelligence.min_temperature,
            "max_c": intelligence.max_temperature,
            "std_dev": intelligence.std_deviation,
            "percentiles": intelligence.percentiles,
        },
        "risk_summary": {
            "overall_level": overall_level,
            "overall_score": overall_score,
            "feature_counts": counts,
            "total_features": len(feature_results),
        },
    }

    data_limitations = [
        "Risk score based solely on average_temperature per tile (FortyGuard Phase 3).",
        "Heat persistence data not available — persistence component not included.",
        "Heat exceedance data not available — exceedance component not included.",
        "CIVICHEAT Decision-Support Risk Score: application-defined heuristic only.",
    ]

    logger.info(
        "Risk engine: complete | overall=%s | score=%d | "
        "low=%d | moderate=%d | high=%d | extreme=%d",
        overall_level,
        overall_score,
        counts["LOW"],
        counts["MODERATE"],
        counts["HIGH"],
        counts["EXTREME"],
    )

    return RiskAnalysisResult(
        city=intelligence.city,
        date=intelligence.date,
        activity_id=intelligence.activity_id,
        data_mode=intelligence.data_mode,
        summary=summary,
        feature_results=feature_results,
        agent_context=agent_context,
        data_limitations=data_limitations,
    )
