"""
CIVICHEAT Reassessment — data models.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Snapshot — one stored analysis result
# ---------------------------------------------------------------------------

class AnalysisSnapshot(BaseModel):
    """
    Compact snapshot of one CIVICHEAT analysis.
    Stored in-memory; structured for future PostgreSQL migration.
    """
    analysis_id: str
    timestamp: datetime
    city: str
    date: str
    data_mode: Literal["LIVE", "DEMO"]

    mean_temperature_c: float
    max_temperature_c: float
    min_temperature_c: float

    overall_risk_level: Literal["LOW", "MODERATE", "HIGH", "EXTREME"]
    overall_risk_score: int

    priority_zone_count: int
    priority_zones: list[dict[str, Any]]   # compact zone summaries


# ---------------------------------------------------------------------------
# Change thresholds — all configurable, all labeled as app-defined
# ---------------------------------------------------------------------------

class ChangeThresholds(BaseModel):
    """
    CIVICHEAT reassessment rules.

    IMPORTANT: These are application-defined decision-support thresholds.
    They are NOT official emergency thresholds.
    """
    risk_score_delta: int = Field(
        5,
        description="Risk score change (points) that triggers meaningful-change flag",
    )
    mean_temperature_delta_c: float = Field(
        1.0,
        description="Mean temperature change (°C) that triggers meaningful-change flag",
    )
    zone_count_change: bool = Field(
        True,
        description="Any change in priority zone count triggers meaningful-change flag",
    )
    zone_rank_shift: int = Field(
        1,
        description="Zone rank shift ≥ this value triggers meaningful-change flag",
    )

    disclaimer: str = (
        "CIVICHEAT reassessment rules — application-defined thresholds. "
        "Not official emergency standards."
    )


# ---------------------------------------------------------------------------
# Comparison result
# ---------------------------------------------------------------------------

class ZoneChange(BaseModel):
    zone_id: str
    previous_rank: int | None
    current_rank: int | None
    previous_score: int | None
    current_score: int | None
    change_type: Literal["new", "removed", "rank_shifted", "score_changed", "unchanged"]


class ComparisonResult(BaseModel):
    """
    Side-by-side comparison of two analysis snapshots.
    All values are derived from real CIVICHEAT data — nothing fabricated.
    """
    previous_snapshot_id: str
    current_snapshot_id: str

    # Temperature deltas
    mean_temperature_change_c: float
    max_temperature_change_c: float

    # Risk deltas
    risk_score_change: int
    previous_risk_score: int
    current_risk_score: int
    previous_risk_level: Literal["LOW", "MODERATE", "HIGH", "EXTREME"]
    current_risk_level: Literal["LOW", "MODERATE", "HIGH", "EXTREME"]

    # Zone changes
    previous_zone_count: int
    current_zone_count: int
    priority_zone_change: int      # signed: positive = more zones
    changed_zones: list[ZoneChange]

    # Decision
    meaningful_change: bool
    change_reasons: list[str]
    thresholds_used: ChangeThresholds

    disclaimer: str = (
        "CIVICHEAT reassessment comparison — application-defined thresholds. "
        "Not an official emergency assessment."
    )


# ---------------------------------------------------------------------------
# Full reassessment response
# ---------------------------------------------------------------------------

class ReassessmentStatus(BaseModel):
    status: Literal["SIGNIFICANT_CHANGE", "NO_SIGNIFICANT_CHANGE"]
    message: str


class ReassessmentResponse(BaseModel):
    """Full response from POST /api/reassessment/run."""
    success: bool
    data_mode: Literal["LIVE", "DEMO"]
    status: ReassessmentStatus
    comparison: ComparisonResult
    previous_snapshot: AnalysisSnapshot | None
    current_snapshot: AnalysisSnapshot

    # Nemotron reassessment decision (only present if meaningful_change=True)
    nemotron_decision: dict[str, Any] | None = None
    nemotron_fallback: bool = False
    tools_used: list[str] = Field(default_factory=list)
