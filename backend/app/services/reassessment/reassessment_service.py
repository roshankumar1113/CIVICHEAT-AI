"""
CIVICHEAT Reassessment Service.

In-memory analysis store + full reassessment pipeline.
Structured for future PostgreSQL migration — just replace the store.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.fortyguard.fortyguard_models import HeatIntelligence
from app.services.heat_risk.risk_models import RiskAnalysisResult
from app.services.priority.priority_models import PriorityAnalysisResult
from app.services.reassessment.comparison_models import AnalysisSnapshot

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory analysis store (swap for DB adapter later)
# ---------------------------------------------------------------------------

class AnalysisStore:
    """
    In-memory store for analysis snapshots.
    Keeps the most recent N analyses per city.
    Designed for easy replacement with a PostgreSQL/PostGIS backend.
    """
    _MAX_PER_CITY = 20

    def __init__(self) -> None:
        self._store: dict[str, list[AnalysisSnapshot]] = {}  # city → [snapshots]

    def save(self, snapshot: AnalysisSnapshot) -> None:
        key = snapshot.city
        if key not in self._store:
            self._store[key] = []
        self._store[key].append(snapshot)
        # Keep only last N
        if len(self._store[key]) > self._MAX_PER_CITY:
            self._store[key] = self._store[key][-self._MAX_PER_CITY:]
        logger.info(
            "AnalysisStore: saved | city=%s | id=%s | score=%d",
            snapshot.city, snapshot.analysis_id, snapshot.overall_risk_score,
        )

    def get_latest(self, city: str) -> AnalysisSnapshot | None:
        snapshots = self._store.get(city, [])
        return snapshots[-1] if snapshots else None

    def get_previous(self, city: str) -> AnalysisSnapshot | None:
        """Return the second-most-recent snapshot (the one before latest)."""
        snapshots = self._store.get(city, [])
        return snapshots[-2] if len(snapshots) >= 2 else None

    def count(self, city: str) -> int:
        return len(self._store.get(city, []))

    def clear(self, city: str | None = None) -> None:
        if city:
            self._store.pop(city, None)
        else:
            self._store.clear()


# Module-level singleton store
_store = AnalysisStore()


def get_analysis_store() -> AnalysisStore:
    return _store


# ---------------------------------------------------------------------------
# Snapshot builder
# ---------------------------------------------------------------------------

def build_snapshot(
    priority_result: PriorityAnalysisResult,
    analysis_id: str | None = None,
) -> AnalysisSnapshot:
    """
    Build a compact AnalysisSnapshot from a PriorityAnalysisResult.
    Only stores summary data — not raw GeoJSON.
    """
    temp = priority_result.agent_context.get("temperature_summary", {})

    compact_zones = [
        {
            "zone_id": z.zone_id,
            "priority_rank": z.priority_rank,
            "risk_level": z.risk_level,
            "risk_score": z.risk_score,
            "feature_count": z.feature_count,
            "temperature_mean_c": z.temperature_mean_c,
        }
        for z in priority_result.priority_zones
    ]

    return AnalysisSnapshot(
        analysis_id=analysis_id or str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        city=priority_result.city,
        date=priority_result.date,
        data_mode=priority_result.data_mode,
        mean_temperature_c=float(temp.get("mean_c", 0)),
        max_temperature_c=float(temp.get("max_c", 0)),
        min_temperature_c=float(temp.get("min_c", 0)),
        overall_risk_level=priority_result.highest_risk_level,
        overall_risk_score=priority_result.highest_risk_score,
        priority_zone_count=len(priority_result.priority_zones),
        priority_zones=compact_zones,
    )
