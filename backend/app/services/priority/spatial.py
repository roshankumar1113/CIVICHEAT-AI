"""
Lightweight spatial utilities.
No heavy GIS dependencies — pure Python geometry using coordinate arithmetic.
"""
from __future__ import annotations
import math


def feature_centroid(geometry: dict) -> tuple[float, float] | None:
    """
    Calculate the centroid of a GeoJSON Polygon geometry.
    Returns (longitude, latitude) or None if geometry is invalid.
    Uses simple arithmetic mean of ring vertices.
    """
    try:
        coords = geometry["coordinates"][0]  # outer ring
        if len(coords) < 3:
            return None
        lon_sum = sum(c[0] for c in coords)
        lat_sum = sum(c[1] for c in coords)
        n = len(coords)
        return (lon_sum / n, lat_sum / n)
    except (KeyError, IndexError, TypeError):
        return None


def feature_bbox(geometry: dict) -> tuple[float, float, float, float] | None:
    """
    Calculate bounding box of a GeoJSON Polygon.
    Returns (west, south, east, north) or None.
    """
    try:
        coords = geometry["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        return (min(lons), min(lats), max(lons), max(lats))
    except (KeyError, IndexError, TypeError):
        return None


def haversine_distance_deg(
    lon1: float, lat1: float, lon2: float, lat2: float
) -> float:
    """
    Fast approximate distance between two points in degrees.
    Avoids trig for performance on hundreds of features.
    Suitable for small-area grouping only.
    """
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    return math.sqrt(dlat * dlat + dlon * dlon)


def merge_bboxes(bboxes: list[tuple[float, float, float, float]]) -> list[float]:
    """Merge a list of (west, south, east, north) into a single bounding box."""
    west = min(b[0] for b in bboxes)
    south = min(b[1] for b in bboxes)
    east = max(b[2] for b in bboxes)
    north = max(b[3] for b in bboxes)
    return [west, south, east, north]


def bbox_centroid(bbox: list[float]) -> list[float]:
    """Return center point of a bounding box as [lon, lat]."""
    return [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2]
