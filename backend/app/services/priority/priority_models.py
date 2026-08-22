"""
Priority zone models.
"""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel

RiskLevel = Literal["LOW", "MODERATE", "HIGH", "EXTREME"]


class PriorityZone(BaseModel):
    """
    A spatially grouped cluster of high-risk FortyGuard tiles.
    Represents a meaningful geographic area for government action.
    """
    zone_id: str                    # e.g. "ZONE-001"
    priority_rank: int              # 1 = highest priority
    risk_score: int                 # 0–100, mean of constituent feature scores
    risk_level: RiskLevel
    feature_count: int              # number of FortyGuard tiles in this zone

    temperature_mean_c: float
    temperature_max_c: float
    temperature_min_c: float

    # Bounding box for quick map filtering [west, south, east, north]
    bbox: list[float]

    # Representative center point [lon, lat]
    centroid: list[float]

    reasons: list[str]
    recommended_actions: list[str]
    action_rationale: str


class PriorityAnalysisResult(BaseModel):
    """Output of the priority engine — consumed by the agent in Phase 4."""
    city: str
    date: str
    activity_id: str
    data_mode: Literal["LIVE", "DEMO"]

    priority_zones: list[PriorityZone]
    total_high_extreme_features: int
    highest_risk_level: RiskLevel
    highest_risk_score: int

    # Full Nemotron-ready context object (Phase 4)
    agent_context: dict[str, Any]
    data_limitations: list[str]
