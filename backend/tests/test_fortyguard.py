"""
Phase 2 tests — FortyGuard adapter and heatmap route.

Tests cover:
  - Demo mode (no API key needed)
  - Parser with real-shaped data
  - Error handling
  - API route (demo mode)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.services.fortyguard.fortyguard_models import (
    ActivityData,
    ActivityStatusData,
    ActivityStatusResponse,
    DateTimeFilter,
    GeoJSONPolygon,
    HeatmapRequest,
    HeatmapResult,
    HeatmapSubmitResponse,
    MapData,
    StatsData,
    TemperatureStats,
    TileFeature,
    TileProperties,
)
from app.services.fortyguard.fortyguard_parser import (
    build_demo_intelligence,
    parse_heat_intelligence,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helper: build a minimal valid ActivityStatusResponse
# ---------------------------------------------------------------------------

def _make_status_response(
    activity_id: str = "test-activity-id",
    avg_temp: float = 40.5,
) -> ActivityStatusResponse:
    feature = TileFeature(
        id="0",
        type="Feature",
        properties=TileProperties(
            tile_id=0,
            average_temperature=avg_temp,
            min_temperature=36.0,
            max_temperature=45.0,
        ),
        geometry={
            "type": "Polygon",
            "coordinates": [[
                [-112.07, 33.44],
                [-112.06, 33.44],
                [-112.06, 33.43],
                [-112.07, 33.43],
                [-112.07, 33.44],
            ]],
        },
    )
    return ActivityStatusResponse(
        error=False,
        status_code=200,
        message="Completed",
        data=ActivityStatusData(
            activity_id=activity_id,
            status="Completed",
            result=HeatmapResult(
                map_data=MapData(type="FeatureCollection", features=[feature]),
                stats_data=StatsData(
                    temperature_stats=TemperatureStats(
                        minimum=36.0,
                        maximum=45.0,
                        mean=avg_temp,
                        standard_deviation=1.2,
                    ),
                    overall_temperature_distribution=[36.0, 39.0, 40.5, 42.0, 45.0],
                ),
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestParser:
    def test_parse_valid_response(self):
        status_resp = _make_status_response(avg_temp=40.5)
        intel = parse_heat_intelligence(status_resp, city="Phoenix, AZ", date="2025-08-01")
        assert intel.city == "Phoenix, AZ"
        assert intel.date == "2025-08-01"
        assert intel.tile_count == 1
        assert intel.mean_temperature == 40.5
        assert intel.min_temperature == 36.0
        assert intel.max_temperature == 45.0
        assert intel.data_mode == "LIVE"
        assert intel.geojson["type"] == "FeatureCollection"
        assert len(intel.geojson["features"]) == 1

    def test_parse_fails_if_not_completed(self):
        status_resp = _make_status_response()
        status_resp.data.status = "Processing"
        status_resp.data.result = None
        with pytest.raises(ValueError, match="status is 'Processing'"):
            parse_heat_intelligence(status_resp, city="Phoenix", date="2025-08-01")

    def test_parse_fails_if_result_missing(self):
        status_resp = _make_status_response()
        status_resp.data.result = None
        with pytest.raises(ValueError, match="result is missing"):
            parse_heat_intelligence(status_resp, city="Phoenix", date="2025-08-01")

    def test_high_risk_temperature(self):
        """Very high temperature (>45°C) should parse correctly."""
        status_resp = _make_status_response(avg_temp=48.0)
        intel = parse_heat_intelligence(status_resp, city="Death Valley", date="2025-08-01")
        assert intel.mean_temperature == 48.0

    def test_moderate_temperature(self):
        """Moderate temperature should parse correctly."""
        status_resp = _make_status_response(avg_temp=32.0)
        intel = parse_heat_intelligence(status_resp, city="Seattle", date="2025-06-01")
        assert intel.mean_temperature == 32.0


# ---------------------------------------------------------------------------
# Demo intelligence tests
# ---------------------------------------------------------------------------

class TestDemoIntelligence:
    def test_demo_returns_correctly_labeled(self):
        demo = build_demo_intelligence()
        assert demo.data_mode == "DEMO"
        assert demo.tile_count > 0
        assert demo.geojson["type"] == "FeatureCollection"

    def test_demo_custom_city_and_date(self):
        demo = build_demo_intelligence(city="Houston, TX", date="2025-07-04")
        assert demo.city == "Houston, TX"
        assert demo.date == "2025-07-04"

    def test_demo_temperatures_are_realistic(self):
        demo = build_demo_intelligence()
        assert demo.mean_temperature > 30, "Demo temps should be hot"
        assert demo.min_temperature < demo.max_temperature


# ---------------------------------------------------------------------------
# API route tests (demo mode — no real API calls)
# ---------------------------------------------------------------------------

class TestHeatmapRoute:
    def test_demo_mode_endpoint(self):
        response = client.post("/api/heatmap", json={
            "city": "Phoenix, AZ",
            "date": "2025-08-01",
            "demo_mode": True,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data_mode"] == "DEMO"
        assert data["intelligence"]["city"] == "Phoenix, AZ"
        assert data["intelligence"]["tile_count"] > 0
        assert "geojson" in data["intelligence"]

    def test_no_api_key_returns_demo(self):
        """Without an API key configured, should silently return demo data."""
        with patch("app.api.routes.heatmap.get_fortyguard_service") as mock_svc:
            svc_instance = MagicMock()
            svc_instance.is_configured.return_value = False
            mock_svc.return_value = svc_instance
            response = client.post("/api/heatmap", json={
                "city": "Phoenix, AZ",
                "date": "2025-08-01",
                "demo_mode": False,
            })
            assert response.status_code == 200
            data = response.json()
            assert data["data_mode"] == "DEMO"

    def test_default_request_uses_phoenix(self):
        response = client.post("/api/heatmap", json={"demo_mode": True})
        assert response.status_code == 200
        data = response.json()
        assert data["intelligence"]["city"] == "Phoenix, AZ"

    def test_custom_city_name(self):
        response = client.post("/api/heatmap", json={
            "city": "Houston, TX",
            "date": "2025-07-15",
            "demo_mode": True,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["intelligence"]["city"] == "Houston, TX"


# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------

class TestModels:
    def test_heatmap_request_serializes(self):
        req = HeatmapRequest(
            polygon_aoi=GeoJSONPolygon(
                type="Polygon",
                coordinates=[[[-112.07, 33.44], [-112.05, 33.44], [-112.05, 33.42], [-112.07, 33.42], [-112.07, 33.44]]],
            ),
            date_time=DateTimeFilter(start_date="2025-08-01", filter_type=3),
        )
        serialized = req.model_dump(exclude_none=True)
        assert serialized["polygon_aoi"]["type"] == "Polygon"
        assert serialized["date_time"]["filter_type"] == 3

    def test_filter_type_must_be_3_or_4(self):
        with pytest.raises(Exception):
            DateTimeFilter(start_date="2025-08-01", filter_type=1)
