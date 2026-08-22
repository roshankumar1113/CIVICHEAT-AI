"""
Phase 3 tests — Heat Risk Engine, Priority Engine, Analysis routes.
All tests use deterministic fixtures — no live API calls required.
"""
from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.fortyguard.fortyguard_models import HeatIntelligence
from app.services.fortyguard.fortyguard_parser import build_demo_intelligence
from app.services.heat_risk.risk_engine import (
    analyze_feature,
    calculate_temperature_score,
    classify_temperature,
    run_risk_analysis,
)
from app.services.heat_risk.risk_rules import TEMPERATURE_THRESHOLDS
from app.services.priority.priority_engine import run_priority_analysis
from app.services.priority.spatial import feature_centroid, feature_bbox, merge_bboxes

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_feature(feature_id: str, avg_temp: float, lon: float = -112.07, lat: float = 33.44) -> dict:
    delta = 0.005
    return {
        "id": feature_id,
        "type": "Feature",
        "properties": {
            "tile_id": int(feature_id),
            "average_temperature": avg_temp,
            "min_temperature": avg_temp - 2.0,
            "max_temperature": avg_temp + 2.0,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [lon, lat + delta],
                [lon + delta, lat + delta],
                [lon + delta, lat],
                [lon, lat],
                [lon, lat + delta],
            ]],
        },
    }


def _make_intelligence(features: list[dict], mean: float = 38.0) -> HeatIntelligence:
    return HeatIntelligence(
        activity_id="test-activity",
        city="Phoenix, AZ",
        date="2025-08-01",
        tile_count=len(features),
        mean_temperature=mean,
        min_temperature=mean - 2.0,
        max_temperature=mean + 2.0,
        std_deviation=1.0,
        percentiles=[mean - 2, mean - 0.5, mean, mean + 0.5, mean + 2],
        geojson={"type": "FeatureCollection", "features": features},
        data_mode="LIVE",
    )


# ---------------------------------------------------------------------------
# Temperature classification
# ---------------------------------------------------------------------------

class TestClassification:
    def test_low_temperature(self):
        t = classify_temperature(20.0)
        assert t.level == "LOW"

    def test_low_boundary(self):
        t = classify_temperature(29.9)
        assert t.level == "LOW"

    def test_moderate_lower_boundary(self):
        t = classify_temperature(30.0)
        assert t.level == "MODERATE"

    def test_moderate_upper_boundary(self):
        t = classify_temperature(34.9)
        assert t.level == "MODERATE"

    def test_high_lower_boundary(self):
        t = classify_temperature(35.0)
        assert t.level == "HIGH"

    def test_high_upper_boundary(self):
        t = classify_temperature(39.9)
        assert t.level == "HIGH"

    def test_extreme_boundary(self):
        t = classify_temperature(40.0)
        assert t.level == "EXTREME"

    def test_extreme_very_hot(self):
        t = classify_temperature(50.0)
        assert t.level == "EXTREME"

    def test_all_thresholds_are_configured(self):
        assert len(TEMPERATURE_THRESHOLDS) == 4
        levels = {t.level for t in TEMPERATURE_THRESHOLDS}
        assert levels == {"LOW", "MODERATE", "HIGH", "EXTREME"}


# ---------------------------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------------------------

class TestRiskScoring:
    def test_low_score_range(self):
        score, threshold = calculate_temperature_score(20.0)
        assert threshold.level == "LOW"
        assert 0 <= score <= 24

    def test_moderate_score_range(self):
        score, threshold = calculate_temperature_score(32.0)
        assert threshold.level == "MODERATE"
        assert 25 <= score <= 49

    def test_high_score_range(self):
        score, threshold = calculate_temperature_score(37.0)
        assert threshold.level == "HIGH"
        assert 50 <= score <= 74

    def test_extreme_score_range(self):
        score, threshold = calculate_temperature_score(42.0)
        assert threshold.level == "EXTREME"
        assert 75 <= score <= 100

    def test_score_is_deterministic(self):
        s1, _ = calculate_temperature_score(38.46)
        s2, _ = calculate_temperature_score(38.46)
        assert s1 == s2

    def test_score_capped_at_100(self):
        score, _ = calculate_temperature_score(999.0)
        assert score <= 100

    def test_score_never_negative(self):
        score, _ = calculate_temperature_score(-50.0)
        assert score >= 0

    def test_higher_temp_higher_score(self):
        s_low, _ = calculate_temperature_score(25.0)
        s_mod, _ = calculate_temperature_score(32.0)
        s_high, _ = calculate_temperature_score(37.0)
        s_ext, _ = calculate_temperature_score(43.0)
        assert s_low < s_mod < s_high < s_ext


# ---------------------------------------------------------------------------
# Feature analysis
# ---------------------------------------------------------------------------

class TestFeatureAnalysis:
    def test_feature_high_risk(self):
        f = _make_feature("1", 38.0)
        result = analyze_feature(f)
        assert result.risk_level == "HIGH"
        assert result.risk_score >= 50
        assert result.temperature_c == 38.0
        assert not result.persistence_available
        assert not result.exceedance_available

    def test_feature_extreme_risk(self):
        f = _make_feature("2", 42.0)
        result = analyze_feature(f)
        assert result.risk_level == "EXTREME"
        assert result.risk_score >= 75

    def test_feature_moderate_risk(self):
        f = _make_feature("3", 32.0)
        result = analyze_feature(f)
        assert result.risk_level == "MODERATE"

    def test_feature_low_risk(self):
        f = _make_feature("4", 22.0)
        result = analyze_feature(f)
        assert result.risk_level == "LOW"

    def test_feature_has_reasons(self):
        f = _make_feature("5", 38.0)
        result = analyze_feature(f)
        assert len(result.reasons) >= 1

    def test_missing_temperature_defaults(self):
        f = {"id": "0", "type": "Feature", "properties": {}, "geometry": {}}
        result = analyze_feature(f)
        assert result.temperature_c == 0.0

    def test_feature_geometry_preserved(self):
        f = _make_feature("6", 36.0)
        result = analyze_feature(f)
        assert result.geometry == f["geometry"]


# ---------------------------------------------------------------------------
# Full risk analysis
# ---------------------------------------------------------------------------

class TestRiskAnalysis:
    def test_all_high_risk(self):
        features = [_make_feature(str(i), 37.0) for i in range(10)]
        intel = _make_intelligence(features, mean=37.0)
        result = run_risk_analysis(intel)
        assert result.summary.overall_risk_level == "HIGH"
        assert result.summary.high_risk_features == 10
        assert result.summary.extreme_risk_features == 0

    def test_all_extreme_risk(self):
        features = [_make_feature(str(i), 42.0) for i in range(5)]
        intel = _make_intelligence(features, mean=42.0)
        result = run_risk_analysis(intel)
        assert result.summary.overall_risk_level == "EXTREME"
        assert result.summary.extreme_risk_features == 5

    def test_all_low_risk(self):
        features = [_make_feature(str(i), 20.0) for i in range(5)]
        intel = _make_intelligence(features, mean=20.0)
        result = run_risk_analysis(intel)
        assert result.summary.overall_risk_level == "LOW"
        assert result.summary.low_risk_features == 5

    def test_mixed_risk_elevates_to_highest(self):
        features = (
            [_make_feature(str(i), 20.0) for i in range(3)]   # LOW
            + [_make_feature(str(i + 3), 42.0) for i in range(1)]  # EXTREME
        )
        intel = _make_intelligence(features)
        result = run_risk_analysis(intel)
        assert result.summary.overall_risk_level == "EXTREME"

    def test_feature_results_match_input_count(self):
        features = [_make_feature(str(i), 38.0) for i in range(20)]
        intel = _make_intelligence(features)
        result = run_risk_analysis(intel)
        assert len(result.feature_results) == 20

    def test_agent_context_present(self):
        features = [_make_feature("0", 38.0)]
        intel = _make_intelligence(features)
        result = run_risk_analysis(intel)
        assert "temperature_summary" in result.agent_context
        assert "risk_summary" in result.agent_context

    def test_data_limitations_present(self):
        features = [_make_feature("0", 38.0)]
        intel = _make_intelligence(features)
        result = run_risk_analysis(intel)
        assert len(result.data_limitations) > 0

    def test_score_disclaimer_present(self):
        features = [_make_feature("0", 38.0)]
        intel = _make_intelligence(features)
        result = run_risk_analysis(intel)
        assert "CIVICHEAT" in result.summary.score_disclaimer


# ---------------------------------------------------------------------------
# Priority zones
# ---------------------------------------------------------------------------

class TestPriorityZones:
    def _run(self, features):
        intel = _make_intelligence(features)
        risk_result = run_risk_analysis(intel)
        return run_priority_analysis(risk_result)

    def test_all_low_risk_no_zones(self):
        features = [_make_feature(str(i), 20.0) for i in range(10)]
        result = self._run(features)
        assert result.priority_zones == [] or all(
            z.risk_level in ("LOW", "MODERATE") for z in result.priority_zones
        )

    def test_clustered_high_risk_forms_zones(self):
        # 10 adjacent HIGH features near same location
        features = [
            _make_feature(str(i), 37.0, lon=-112.07 + i * 0.003, lat=33.44)
            for i in range(10)
        ]
        result = self._run(features)
        assert len(result.priority_zones) >= 1

    def test_zones_ranked_by_score(self):
        # Mix of temperatures — hottest cluster should be rank 1
        features = (
            [_make_feature(str(i), 41.0, lon=-112.07 + i * 0.003, lat=33.44) for i in range(5)]  # EXTREME
            + [_make_feature(str(i + 5), 36.0, lon=-112.03 + i * 0.003, lat=33.44) for i in range(5)]  # HIGH
        )
        result = self._run(features)
        if len(result.priority_zones) >= 2:
            assert result.priority_zones[0].risk_score >= result.priority_zones[1].risk_score

    def test_zone_has_required_fields(self):
        features = [
            _make_feature(str(i), 37.0, lon=-112.07 + i * 0.003, lat=33.44)
            for i in range(5)
        ]
        result = self._run(features)
        if result.priority_zones:
            z = result.priority_zones[0]
            assert z.zone_id.startswith("ZONE-")
            assert z.priority_rank == 1
            assert 0 <= z.risk_score <= 100
            assert z.feature_count > 0
            assert len(z.recommended_actions) > 0
            assert len(z.reasons) > 0

    def test_government_actions_in_context(self):
        features = [_make_feature(str(i), 37.0, lon=-112.07 + i * 0.003, lat=33.44) for i in range(5)]
        result = self._run(features)
        assert "government_actions" in result.agent_context


# ---------------------------------------------------------------------------
# Spatial utilities
# ---------------------------------------------------------------------------

class TestSpatialUtils:
    def test_centroid_simple_polygon(self):
        geo = {
            "type": "Polygon",
            "coordinates": [[[-112.07, 33.44], [-112.06, 33.44], [-112.06, 33.43], [-112.07, 33.43], [-112.07, 33.44]]],
        }
        c = feature_centroid(geo)
        assert c is not None
        assert abs(c[0] - (-112.065)) < 0.001
        assert abs(c[1] - 33.435) < 0.001

    def test_centroid_invalid_returns_none(self):
        assert feature_centroid({}) is None
        assert feature_centroid({"coordinates": [[]]}) is None

    def test_bbox_simple_polygon(self):
        geo = {
            "type": "Polygon",
            "coordinates": [[[-112.07, 33.44], [-112.06, 33.44], [-112.06, 33.43], [-112.07, 33.43], [-112.07, 33.44]]],
        }
        bb = feature_bbox(geo)
        assert bb is not None
        assert bb[0] == pytest.approx(-112.07)
        assert bb[2] == pytest.approx(-112.06)

    def test_merge_bboxes(self):
        bboxes = [(-112.07, 33.43, -112.06, 33.44), (-112.05, 33.42, -112.04, 33.45)]
        result = merge_bboxes(bboxes)
        assert result[0] == pytest.approx(-112.07)
        assert result[3] == pytest.approx(33.45)


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

class TestRiskRoute:
    def test_risk_analyze_with_demo_data(self):
        demo = build_demo_intelligence()
        response = client.post("/api/risk/analyze", json=demo.model_dump())
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "feature_results" in data
        assert data["summary"]["total_features"] == demo.tile_count

    def test_risk_analyze_returns_disclaimer(self):
        demo = build_demo_intelligence()
        response = client.post("/api/risk/analyze", json=demo.model_dump())
        assert response.status_code == 200
        data = response.json()
        assert "CIVICHEAT" in data["summary"]["score_disclaimer"]


class TestAnalysisRoute:
    def test_full_analysis_demo_mode(self):
        response = client.post("/api/heatmap/analyze", json={
            "city": "Phoenix, AZ",
            "date": "2025-08-01",
            "demo_mode": True,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data_mode"] == "DEMO"
        assert "result" in data
        result = data["result"]
        assert "priority_zones" in result
        assert "highest_risk_level" in result
        assert "agent_context" in result

    def test_full_analysis_returns_limitations(self):
        response = client.post("/api/heatmap/analyze", json={"demo_mode": True})
        assert response.status_code == 200
        data = response.json()
        assert len(data["result"]["data_limitations"]) > 0

    def test_full_analysis_no_fake_claims(self):
        response = client.post("/api/heatmap/analyze", json={"demo_mode": True})
        body_str = response.text
        # Make sure we didn't introduce any hardcoded impact claims
        for forbidden in ["100,000 lives", "95% accuracy", "guaranteed reduction"]:
            assert forbidden not in body_str
