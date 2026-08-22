"""
Transforms raw FortyGuard API responses into clean HeatIntelligence objects.
All values are directly derived from API data — nothing is fabricated.
"""
from __future__ import annotations

import logging
from typing import Any

from app.services.fortyguard.fortyguard_models import (
    ActivityStatusResponse,
    HeatIntelligence,
)

logger = logging.getLogger(__name__)


def parse_heat_intelligence(
    status_response: ActivityStatusResponse,
    city: str,
    date: str,
) -> HeatIntelligence:
    """
    Convert a completed FortyGuard status response into a HeatIntelligence object.

    Raises ValueError if the result is missing or incomplete.
    """
    data = status_response.data

    if data.status != "Completed":
        raise ValueError(f"Cannot parse result: activity status is '{data.status}'")

    if data.result is None:
        raise ValueError("Activity completed but result is missing")

    result = data.result
    stats = result.stats_data.temperature_stats
    map_data = result.map_data

    # Build GeoJSON FeatureCollection for frontend rendering
    geojson: dict[str, Any] = {
        "type": "FeatureCollection",
        "features": [
            f.model_dump() for f in map_data.features
        ],
    }

    intelligence = HeatIntelligence(
        activity_id=data.activity_id,
        city=city,
        date=date,
        tile_count=len(map_data.features),
        mean_temperature=round(stats.mean, 4),
        min_temperature=round(stats.minimum, 4),
        max_temperature=round(stats.maximum, 4),
        std_deviation=round(stats.standard_deviation, 6),
        percentiles=result.stats_data.overall_temperature_distribution,
        geojson=geojson,
        data_mode="LIVE",
    )

    logger.info(
        "FortyGuard: parsed intelligence | city=%s | date=%s | tiles=%d | "
        "mean=%.2f°C | min=%.2f°C | max=%.2f°C",
        city,
        date,
        intelligence.tile_count,
        intelligence.mean_temperature,
        intelligence.min_temperature,
        intelligence.max_temperature,
    )

    return intelligence


def build_demo_intelligence(city: str = "Phoenix, AZ", date: str = "2025-08-01") -> HeatIntelligence:
    """
    Returns a minimal demo HeatIntelligence object using a small cached polygon.
    Used when FortyGuard API is unavailable or in DEMO mode.
    Clearly labeled as DEMO data.
    """
    # Small representative Phoenix polygon (real coordinates)
    demo_features = [
        {
            "id": "demo_0",
            "type": "Feature",
            "properties": {
                "tile_id": 0,
                "average_temperature": 42.1,
                "min_temperature": 38.5,
                "max_temperature": 45.8,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-112.074, 33.4484],
                    [-112.064, 33.4484],
                    [-112.064, 33.4384],
                    [-112.074, 33.4384],
                    [-112.074, 33.4484],
                ]],
            },
        },
        {
            "id": "demo_1",
            "type": "Feature",
            "properties": {
                "tile_id": 1,
                "average_temperature": 43.7,
                "min_temperature": 39.2,
                "max_temperature": 47.1,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-112.064, 33.4484],
                    [-112.054, 33.4484],
                    [-112.054, 33.4384],
                    [-112.064, 33.4384],
                    [-112.064, 33.4484],
                ]],
            },
        },
        {
            "id": "demo_2",
            "type": "Feature",
            "properties": {
                "tile_id": 2,
                "average_temperature": 44.9,
                "min_temperature": 40.1,
                "max_temperature": 48.3,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-112.074, 33.4384],
                    [-112.064, 33.4384],
                    [-112.064, 33.4284],
                    [-112.074, 33.4284],
                    [-112.074, 33.4384],
                ]],
            },
        },
    ]

    return HeatIntelligence(
        activity_id="demo-00000000-0000-0000-0000-000000000000",
        city=city,
        date=date,
        tile_count=len(demo_features),
        mean_temperature=43.57,
        min_temperature=38.5,
        max_temperature=48.3,
        std_deviation=2.1,
        percentiles=[38.5, 42.1, 43.7, 44.9, 48.3],
        geojson={"type": "FeatureCollection", "features": demo_features},
        data_mode="DEMO",
    )
