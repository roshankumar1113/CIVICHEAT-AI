"""
Pydantic models for the FortyGuard API.
Based on verified API contract — do not guess undocumented fields.
"""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class DateTimeFilter(BaseModel):
    """
    filter_type values (verified):
      3 = single day  (start_date only)
      4 = date range  (start_date + end_date)
    1 and 2 return 500 from the API — do not use.
    """
    start_date: str = Field(..., description="ISO date string: YYYY-MM-DD")
    filter_type: Literal[3, 4] = Field(3, description="3=single day, 4=date range")
    end_date: str | None = Field(None, description="Required for filter_type=4")


class GeoJSONPolygon(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[list[float]]]


class HeatmapRequest(BaseModel):
    polygon_aoi: GeoJSONPolygon
    date_time: DateTimeFilter


# ---------------------------------------------------------------------------
# Response models — submit
# ---------------------------------------------------------------------------

class ActivityData(BaseModel):
    activity_id: str


class HeatmapSubmitResponse(BaseModel):
    error: bool
    status_code: int
    message: str
    data: ActivityData


# ---------------------------------------------------------------------------
# Response models — status / result
# ---------------------------------------------------------------------------

class TileProperties(BaseModel):
    tile_id: int
    average_temperature: float
    min_temperature: float
    max_temperature: float


class TileFeature(BaseModel):
    id: str
    type: Literal["Feature"]
    properties: TileProperties
    geometry: dict[str, Any]


class MapData(BaseModel):
    type: Literal["FeatureCollection"]
    features: list[TileFeature]


class TemperatureStats(BaseModel):
    minimum: float
    maximum: float
    mean: float
    standard_deviation: float


class StatsData(BaseModel):
    temperature_stats: TemperatureStats
    overall_temperature_distribution: list[float] = Field(default_factory=list)
    normal_temperature_distribution: dict[str, Any] = Field(default_factory=dict)
    temperature_frequency: dict[str, Any] = Field(default_factory=dict)


class HeatmapResult(BaseModel):
    map_data: MapData
    stats_data: StatsData


class ActivityStatusData(BaseModel):
    activity_id: str
    status: str        # "Processing" | "Completed" | "Failed"
    result: HeatmapResult | None = None


class ActivityStatusResponse(BaseModel):
    error: bool
    status_code: int
    message: str
    data: ActivityStatusData


# ---------------------------------------------------------------------------
# Parsed / normalised intelligence object
# ---------------------------------------------------------------------------

class HeatIntelligence(BaseModel):
    """
    Clean heat intelligence object consumed by the rest of the application.
    All values are directly derived from FortyGuard data.
    """
    activity_id: str
    city: str
    date: str
    tile_count: int

    # Aggregated temperature values (°C)
    mean_temperature: float
    min_temperature: float
    max_temperature: float
    std_deviation: float

    # Percentile distribution [p0, p25, p50, p75, p100]
    percentiles: list[float]

    # Raw GeoJSON for map rendering
    geojson: dict[str, Any]

    # Source data mode
    data_mode: Literal["LIVE", "DEMO"] = "LIVE"
