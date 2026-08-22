"""
Pydantic models for the CIVICHEAT heat risk layer.
"""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

RiskLevel = Literal["LOW", "MODERATE", "HIGH", "EXTREME"]


class FeatureRiskResult(BaseModel):
    """Risk assessment for a single FortyGuard tile feature."""
    feature_id: str
    temperature_c: float
    risk_level: RiskLevel
    risk_score: int          # 0–100, CIVICHEAT Decision-Support Risk Score
    reasons: list[str]

    # Components — only temperature is available in Phase 3
    temperature_component: float
    persistence_available: bool = False
    exceedance_available: bool = False

    # Pass-through geometry for downstream consumers
    geometry: dict[str, Any]


class AnalysisSummary(BaseModel):
    """Aggregate statistics across all analyzed features."""
    total_features: int
    mean_temperature_c: float
    max_temperature_c: float
    min_temperature_c: float

    low_risk_features: int
    moderate_risk_features: int
    high_risk_features: int
    extreme_risk_features: int

    overall_risk_level: RiskLevel
    overall_risk_score: int

    persistence_available: bool = False
    exceedance_available: bool = False
    score_disclaimer: str


class RiskAnalysisResult(BaseModel):
    """Full risk analysis output — input to the priority engine."""
    city: str
    date: str
    activity_id: str
    data_mode: Literal["LIVE", "DEMO"]

    summary: AnalysisSummary
    feature_results: list[FeatureRiskResult]

    # Clean context object for Nemotron agent (Phase 4)
    agent_context: dict[str, Any] = Field(default_factory=dict)

    data_limitations: list[str] = Field(default_factory=list)
