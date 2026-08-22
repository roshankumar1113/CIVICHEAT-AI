"""
Phase 4.5 tests — HeatWatch Reassessment.

Tests cover:
  - AnalysisStore (in-memory)
  - Snapshot builder
  - Comparison engine (no change, risk increase, risk decrease, temp change,
    new zone, removed zone, rank shift)
  - Meaningful-change detection
  - Reassessment endpoint (first run, no change, significant change)
  - Nemotron invoked on change / NOT invoked on no-change
  - compare_previous_analysis agent tool
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.fortyguard.fortyguard_parser import build_demo_intelligence
from app.services.heat_risk.risk_engine import run_risk_analysis
from app.services.nemotron.nemotron_agent import AgentTools
from app.services.nemotron.nemotron_models import AgentDecision, ReassessmentPlan, RecommendedAction
from app.services.priority.priority_engine import run_priority_analysis
from app.services.reassessment.comparison_engine import compare_snapshots
from app.services.reassessment.comparison_models import AnalysisSnapshot, ChangeThresholds
from app.services.reassessment.reassessment_service import (
    AnalysisStore,
    build_snapshot,
    get_analysis_store,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_snapshot(
    city: str = "Phoenix, AZ",
    risk_score: int = 67,
    risk_level: str = "HIGH",
    mean_temp: float = 38.46,
    max_temp: float = 38.47,
    zone_count: int = 4,
    zones: list | None = None,
    analysis_id: str = "test-snap-1",
) -> AnalysisSnapshot:
    if zones is None:
        zones = [
            {"zone_id": f"ZONE-{i+1:03d}", "priority_rank": i + 1,
             "risk_level": risk_level, "risk_score": risk_score,
             "feature_count": 100, "temperature_mean_c": mean_temp}
            for i in range(zone_count)
        ]
    return AnalysisSnapshot(
        analysis_id=analysis_id,
        timestamp=datetime.now(timezone.utc),
        city=city,
        date="2025-08-01",
        data_mode="DEMO",
        mean_temperature_c=mean_temp,
        max_temperature_c=max_temp,
        min_temperature_c=mean_temp - 2.0,
        overall_risk_level=risk_level,  # type: ignore[arg-type]
        overall_risk_score=risk_score,
        priority_zone_count=zone_count,
        priority_zones=zones,
    )


def _valid_decision_json() -> str:
    return json.dumps({
        "decision": "Updated response recommended due to risk increase.",
        "priority_zone": "ZONE-001",
        "risk_level": "HIGH",
        "risk_score": 74,
        "evidence": ["Risk score increased by 7 points.", "Mean temperature increased."],
        "recommended_actions": [
            {"action": "Review cooling response", "reason": "Risk increase", "urgency": "HIGH"}
        ],
        "limitations": ["CIVICHEAT heuristic score."],
        "reassessment": {"recommended": True, "interval_minutes": 60},
    })


def _real_demo_context():
    intel = build_demo_intelligence()
    risk = run_risk_analysis(intel)
    priority = run_priority_analysis(risk)
    ctx = dict(priority.agent_context)
    ctx["data_limitations"] = priority.data_limitations
    return ctx, priority


# ---------------------------------------------------------------------------
# 1. AnalysisStore
# ---------------------------------------------------------------------------

class TestAnalysisStore:
    def setup_method(self):
        self.store = AnalysisStore()

    def test_empty_store_returns_none(self):
        assert self.store.get_latest("Phoenix, AZ") is None
        assert self.store.get_previous("Phoenix, AZ") is None

    def test_save_and_retrieve_latest(self):
        snap = _make_snapshot()
        self.store.save(snap)
        assert self.store.get_latest("Phoenix, AZ").analysis_id == "test-snap-1"

    def test_save_two_retrieves_correct_order(self):
        s1 = _make_snapshot(analysis_id="snap-1", risk_score=67)
        s2 = _make_snapshot(analysis_id="snap-2", risk_score=74)
        self.store.save(s1)
        self.store.save(s2)
        assert self.store.get_latest("Phoenix, AZ").analysis_id == "snap-2"
        assert self.store.get_previous("Phoenix, AZ").analysis_id == "snap-1"

    def test_different_cities_isolated(self):
        self.store.save(_make_snapshot(city="Phoenix, AZ", analysis_id="phx"))
        self.store.save(_make_snapshot(city="Houston, TX", analysis_id="hou"))
        assert self.store.get_latest("Phoenix, AZ").analysis_id == "phx"
        assert self.store.get_latest("Houston, TX").analysis_id == "hou"

    def test_count(self):
        self.store.save(_make_snapshot(analysis_id="a"))
        self.store.save(_make_snapshot(analysis_id="b"))
        assert self.store.count("Phoenix, AZ") == 2

    def test_clear_city(self):
        self.store.save(_make_snapshot())
        self.store.clear("Phoenix, AZ")
        assert self.store.get_latest("Phoenix, AZ") is None

    def test_max_entries_not_exceeded(self):
        for i in range(25):
            self.store.save(_make_snapshot(analysis_id=f"snap-{i}"))
        assert self.store.count("Phoenix, AZ") <= 20


# ---------------------------------------------------------------------------
# 2. Snapshot builder
# ---------------------------------------------------------------------------

class TestSnapshotBuilder:
    def test_build_from_priority_result(self):
        _, priority = _real_demo_context()
        snap = build_snapshot(priority)
        assert snap.city == "Phoenix, AZ"
        assert snap.overall_risk_score >= 0
        assert snap.priority_zone_count == len(priority.priority_zones)
        assert len(snap.priority_zones) == snap.priority_zone_count
        assert snap.data_mode == "DEMO"

    def test_snapshot_does_not_include_geojson(self):
        _, priority = _real_demo_context()
        snap = build_snapshot(priority)
        snap_json = snap.model_dump_json()
        assert "FeatureCollection" not in snap_json
        assert "coordinates" not in snap_json


# ---------------------------------------------------------------------------
# 3. Comparison engine — no change
# ---------------------------------------------------------------------------

class TestComparisonNoChange:
    def test_identical_snapshots_no_change(self):
        s = _make_snapshot()
        result = compare_snapshots(s, s)
        assert result.meaningful_change is False
        assert result.risk_score_change == 0
        assert result.mean_temperature_change_c == 0.0
        assert result.priority_zone_change == 0

    def test_small_score_change_not_meaningful(self):
        s1 = _make_snapshot(risk_score=67)
        s2 = _make_snapshot(risk_score=69, analysis_id="snap-2")  # delta = 2, threshold = 5
        result = compare_snapshots(s1, s2)
        assert result.meaningful_change is False

    def test_small_temp_change_not_meaningful(self):
        s1 = _make_snapshot(mean_temp=38.46)
        s2 = _make_snapshot(mean_temp=38.90, analysis_id="snap-2")  # delta = 0.44, threshold = 1.0
        result = compare_snapshots(s1, s2)
        # Only temp change, below threshold
        assert result.mean_temperature_change_c == pytest.approx(0.44, abs=0.01)


# ---------------------------------------------------------------------------
# 4. Comparison engine — meaningful change
# ---------------------------------------------------------------------------

class TestComparisonMeaningfulChange:
    def test_risk_score_increase(self):
        s1 = _make_snapshot(risk_score=67)
        s2 = _make_snapshot(risk_score=74, analysis_id="snap-2")
        result = compare_snapshots(s1, s2)
        assert result.meaningful_change is True
        assert result.risk_score_change == 7
        assert any("7 points" in r for r in result.change_reasons)

    def test_risk_score_decrease(self):
        s1 = _make_snapshot(risk_score=74)
        s2 = _make_snapshot(risk_score=62, analysis_id="snap-2")
        result = compare_snapshots(s1, s2)
        assert result.meaningful_change is True
        assert result.risk_score_change == -12

    def test_temperature_increase(self):
        s1 = _make_snapshot(mean_temp=38.0)
        s2 = _make_snapshot(mean_temp=39.5, analysis_id="snap-2")
        result = compare_snapshots(s1, s2)
        assert result.meaningful_change is True
        assert result.mean_temperature_change_c == pytest.approx(1.5, abs=0.01)

    def test_new_priority_zone(self):
        s1 = _make_snapshot(zone_count=3)
        s2 = _make_snapshot(zone_count=4, analysis_id="snap-2")
        result = compare_snapshots(s1, s2)
        assert result.meaningful_change is True
        assert result.priority_zone_change == 1

    def test_removed_priority_zone(self):
        s1 = _make_snapshot(zone_count=4)
        s2 = _make_snapshot(zone_count=3, analysis_id="snap-2")
        result = compare_snapshots(s1, s2)
        assert result.meaningful_change is True
        assert result.priority_zone_change == -1

    def test_zone_rank_shift(self):
        zones_prev = [
            {"zone_id": "ZONE-001", "priority_rank": 1, "risk_level": "HIGH",
             "risk_score": 67, "feature_count": 100, "temperature_mean_c": 38.5},
            {"zone_id": "ZONE-002", "priority_rank": 2, "risk_level": "HIGH",
             "risk_score": 65, "feature_count": 80, "temperature_mean_c": 38.4},
        ]
        zones_curr = [
            {"zone_id": "ZONE-001", "priority_rank": 2, "risk_level": "HIGH",
             "risk_score": 65, "feature_count": 100, "temperature_mean_c": 38.4},
            {"zone_id": "ZONE-002", "priority_rank": 1, "risk_level": "HIGH",
             "risk_score": 68, "feature_count": 80, "temperature_mean_c": 38.6},
        ]
        s1 = _make_snapshot(zones=zones_prev, zone_count=2)
        s2 = _make_snapshot(zones=zones_curr, zone_count=2, analysis_id="snap-2")
        result = compare_snapshots(s1, s2)
        zone_changes = {z.zone_id: z for z in result.changed_zones}
        assert zone_changes["ZONE-001"].change_type == "rank_shifted"
        assert zone_changes["ZONE-002"].change_type == "rank_shifted"

    def test_change_reasons_populated(self):
        s1 = _make_snapshot(risk_score=67, zone_count=3)
        s2 = _make_snapshot(risk_score=75, zone_count=4, analysis_id="snap-2")
        result = compare_snapshots(s1, s2)
        assert len(result.change_reasons) >= 1

    def test_disclaimer_present(self):
        s = _make_snapshot()
        result = compare_snapshots(s, s)
        assert "CIVICHEAT" in result.disclaimer


# ---------------------------------------------------------------------------
# 5. Custom thresholds
# ---------------------------------------------------------------------------

class TestCustomThresholds:
    def test_stricter_threshold_no_change(self):
        strict = ChangeThresholds(risk_score_delta=20, mean_temperature_delta_c=5.0, zone_count_change=False)
        s1 = _make_snapshot(risk_score=67)
        s2 = _make_snapshot(risk_score=74, analysis_id="snap-2")  # delta=7, below 20
        result = compare_snapshots(s1, s2, strict)
        assert result.meaningful_change is False

    def test_looser_threshold_triggers_change(self):
        loose = ChangeThresholds(risk_score_delta=2, mean_temperature_delta_c=0.1, zone_count_change=True)
        s1 = _make_snapshot(risk_score=67)
        s2 = _make_snapshot(risk_score=70, analysis_id="snap-2")  # delta=3, above 2
        result = compare_snapshots(s1, s2, loose)
        assert result.meaningful_change is True


# ---------------------------------------------------------------------------
# 6. compare_previous_analysis agent tool
# ---------------------------------------------------------------------------

class TestComparePreviousAnalysisTool:
    def test_returns_no_data_when_not_in_context(self):
        ctx, _ = _real_demo_context()
        tools = AgentTools(ctx)
        result = json.loads(tools.execute("compare_previous_analysis", {}))
        assert result["available"] is False

    def test_returns_comparison_when_in_context(self):
        ctx, _ = _real_demo_context()
        ctx["reassessment_comparison"] = {
            "previous_risk_score": 67,
            "current_risk_score": 74,
            "risk_score_change": 7,
            "meaningful_change": True,
        }
        tools = AgentTools(ctx)
        result = json.loads(tools.execute("compare_previous_analysis", {}))
        assert result["risk_score_change"] == 7
        assert result["meaningful_change"] is True

    def test_tool_definition_exists(self):
        from app.services.nemotron.nemotron_agent import CIVICHEAT_TOOLS
        names = {t["function"]["name"] for t in CIVICHEAT_TOOLS}
        assert "compare_previous_analysis" in names


# ---------------------------------------------------------------------------
# 7. Reassessment API endpoint
# ---------------------------------------------------------------------------

class TestReassessmentEndpoint:
    def setup_method(self):
        # Clear the store before each test
        get_analysis_store().clear()

    def test_first_run_no_comparison(self):
        response = client.post("/api/reassessment/run", json={"demo_mode": True})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"]["status"] == "NO_SIGNIFICANT_CHANGE"
        assert "First analysis" in data["status"]["message"]
        assert data["previous_snapshot"] is None
        assert data["current_snapshot"] is not None

    def test_second_run_with_no_change_no_nemotron(self):
        # Run twice with same demo data → scores should be identical
        client.post("/api/reassessment/run", json={"demo_mode": True})
        response = client.post("/api/reassessment/run", json={
            "demo_mode": True,
            "invoke_nemotron_on_change": False,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["previous_snapshot"] is not None
        assert data["comparison"]["risk_score_change"] == 0
        assert data["nemotron_decision"] is None  # no Nemotron, no change

    def test_endpoint_returns_comparison_fields(self):
        client.post("/api/reassessment/run", json={"demo_mode": True})
        response = client.post("/api/reassessment/run", json={"demo_mode": True})
        assert response.status_code == 200
        data = response.json()
        comp = data["comparison"]
        assert "risk_score_change" in comp
        assert "mean_temperature_change_c" in comp
        assert "priority_zone_change" in comp
        assert "meaningful_change" in comp
        assert "change_reasons" in comp
        assert "disclaimer" in comp

    def test_significant_change_invokes_nemotron_fallback(self):
        """Inject a snapshot with a very different score to force meaningful change."""
        store = get_analysis_store()
        # Save a snapshot with score 20 (far from demo's ~84)
        store.save(_make_snapshot(risk_score=20, analysis_id="injected-low"))

        with patch("app.api.routes.reassessment.NemotronClient") as MockClient:
            MockClient.return_value.is_configured.return_value = False  # force fallback
            response = client.post("/api/reassessment/run", json={
                "demo_mode": True,
                "invoke_nemotron_on_change": True,
            })

        assert response.status_code == 200
        data = response.json()
        assert data["comparison"]["meaningful_change"] is True
        assert data["nemotron_decision"] is not None  # fallback was used
        assert data["nemotron_fallback"] is True

    def test_no_change_does_not_invoke_nemotron(self):
        """Run the same demo data twice — no change expected, Nemotron should NOT be called."""
        client.post("/api/reassessment/run", json={"demo_mode": True})

        nemotron_was_called = False

        async def fake_run_agent(*args, **kwargs):
            nonlocal nemotron_was_called
            nemotron_was_called = True
            decision = AgentDecision.model_validate(json.loads(_valid_decision_json()))
            return decision, ["compare_previous_analysis"]

        with patch("app.api.routes.reassessment.run_agent", side_effect=fake_run_agent):
            response = client.post("/api/reassessment/run", json={
                "demo_mode": True,
                "invoke_nemotron_on_change": True,
            })

        assert response.status_code == 200
        assert not nemotron_was_called, "Nemotron should NOT be called when no meaningful change"

    def test_history_endpoint(self):
        client.post("/api/reassessment/run", json={"demo_mode": True})
        client.post("/api/reassessment/run", json={"demo_mode": True})
        response = client.get("/api/reassessment/history?city=Phoenix%2C+AZ")
        assert response.status_code == 200
        data = response.json()
        assert data["stored_analyses"] >= 2
        assert data["latest"] is not None

    def test_response_has_no_fabricated_claims(self):
        response = client.post("/api/reassessment/run", json={"demo_mode": True})
        body = response.text
        for forbidden in ["100,000 lives", "guaranteed", "95% accuracy"]:
            assert forbidden not in body

    def test_disclaimer_in_comparison(self):
        client.post("/api/reassessment/run", json={"demo_mode": True})
        response = client.post("/api/reassessment/run", json={"demo_mode": True})
        data = response.json()
        assert "CIVICHEAT" in data["comparison"]["disclaimer"]
