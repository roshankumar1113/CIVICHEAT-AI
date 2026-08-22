"""
CIVICHEAT Priority Zone Engine.

Groups high-risk FortyGuard tile features into meaningful geographic zones
and ranks them for government decision-making.

Algorithm:
1. Filter features to HIGH + EXTREME risk only.
2. Sort by risk score descending.
3. Greedily cluster nearby features (centroid distance threshold).
4. For each cluster: compute aggregate stats + recommendations.
5. Rank clusters by mean risk score descending.
"""
from __future__ import annotations

import logging
from typing import Literal

from app.services.heat_risk.government_actions import (
    get_action_rationale,
    get_recommended_actions,
)
from app.services.heat_risk.risk_models import FeatureRiskResult, RiskAnalysisResult
from app.services.heat_risk.risk_rules import (
    MAX_PRIORITY_ZONES,
    MIN_ZONE_FEATURE_COUNT,
    ZONE_GROUPING_DISTANCE_DEG,
)
from app.services.priority.priority_models import PriorityAnalysisResult, PriorityZone
from app.services.priority.spatial import (
    bbox_centroid,
    feature_bbox,
    feature_centroid,
    haversine_distance_deg,
    merge_bboxes,
)

logger = logging.getLogger(__name__)

RiskLevel = Literal["LOW", "MODERATE", "HIGH", "EXTREME"]
_RISK_ORDER: dict[str, int] = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "EXTREME": 3}


def _highest_risk(levels: list[str]) -> RiskLevel:
    return max(levels, key=lambda l: _RISK_ORDER.get(l, 0))  # type: ignore[return-value]


def _cluster_features(
    candidates: list[FeatureRiskResult],
    distance_threshold: float,
) -> list[list[FeatureRiskResult]]:
    """
    Greedy centroid-distance clustering.
    No external dependencies — pure Python.
    Each un-assigned feature either starts a new cluster or joins
    the nearest existing one within distance_threshold degrees.
    """
    # Pre-compute centroids
    centroids: list[tuple[float, float] | None] = [
        feature_centroid(f.geometry) for f in candidates
    ]

    clusters: list[list[int]] = []           # list of index lists
    cluster_centroids: list[list[float]] = []  # running mean centroid per cluster

    for i, centroid in enumerate(centroids):
        if centroid is None:
            # No geometry — put in its own single-feature cluster
            clusters.append([i])
            cluster_centroids.append([0.0, 0.0])
            continue

        best_cluster = None
        best_dist = float("inf")
        for ci, cc in enumerate(cluster_centroids):
            if not cc:
                continue
            d = haversine_distance_deg(centroid[0], centroid[1], cc[0], cc[1])
            if d < distance_threshold and d < best_dist:
                best_dist = d
                best_cluster = ci

        if best_cluster is not None:
            clusters[best_cluster].append(i)
            # Update running mean centroid
            n = len(clusters[best_cluster])
            cc = cluster_centroids[best_cluster]
            cluster_centroids[best_cluster] = [
                (cc[0] * (n - 1) + centroid[0]) / n,
                (cc[1] * (n - 1) + centroid[1]) / n,
            ]
        else:
            clusters.append([i])
            cluster_centroids.append(list(centroid))

    return [[candidates[i] for i in cluster] for cluster in clusters]


def _build_zone(
    cluster: list[FeatureRiskResult],
    rank: int,
) -> PriorityZone:
    """Convert a cluster of FeatureRiskResults into a PriorityZone."""
    temps = [f.temperature_c for f in cluster]
    scores = [f.risk_score for f in cluster]
    levels = [f.risk_level for f in cluster]

    mean_temp = round(sum(temps) / len(temps), 2)
    max_temp = round(max(temps), 2)
    min_temp = round(min(temps), 2)
    mean_score = round(sum(scores) / len(scores))
    zone_risk: RiskLevel = _highest_risk(levels)

    # Bounding box
    valid_bboxes = [
        bb for f in cluster
        if (bb := feature_bbox(f.geometry)) is not None
    ]
    if valid_bboxes:
        bbox = merge_bboxes(valid_bboxes)
    else:
        bbox = [0.0, 0.0, 0.0, 0.0]

    centroid = bbox_centroid(bbox)
    zone_id = f"ZONE-{rank:03d}"

    reasons = [
        f"Cluster of {len(cluster)} elevated-temperature tile(s).",
        f"Mean temperature: {mean_temp:.1f}°C, peak: {max_temp:.1f}°C.",
        f"Dominant risk classification: {zone_risk}.",
    ]
    if len(cluster) >= MIN_ZONE_FEATURE_COUNT:
        reasons.append(
            f"Geographic concentration: {len(cluster)} contiguous tiles in affected area."
        )

    actions = get_recommended_actions(zone_risk)
    rationale = get_action_rationale(zone_risk, mean_temp)

    return PriorityZone(
        zone_id=zone_id,
        priority_rank=rank,
        risk_score=mean_score,
        risk_level=zone_risk,
        feature_count=len(cluster),
        temperature_mean_c=mean_temp,
        temperature_max_c=max_temp,
        temperature_min_c=min_temp,
        bbox=bbox,
        centroid=centroid,
        reasons=reasons,
        recommended_actions=actions,
        action_rationale=rationale,
    )


def run_priority_analysis(risk_result: RiskAnalysisResult) -> PriorityAnalysisResult:
    """
    Entry point: takes a RiskAnalysisResult, produces PriorityAnalysisResult.
    """
    logger.info(
        "Priority engine: processing %d features | city=%s",
        len(risk_result.feature_results),
        risk_result.city,
    )

    # Only cluster HIGH and EXTREME features into zones
    candidates = [
        f for f in risk_result.feature_results
        if f.risk_level in ("HIGH", "EXTREME")
    ]

    total_high_extreme = len(candidates)
    logger.info("Priority engine: %d HIGH/EXTREME features to cluster", total_high_extreme)

    priority_zones: list[PriorityZone] = []

    if candidates:
        # Sort by score descending before clustering so highest-risk seeds clusters
        candidates_sorted = sorted(candidates, key=lambda f: f.risk_score, reverse=True)

        clusters = _cluster_features(candidates_sorted, ZONE_GROUPING_DISTANCE_DEG)

        # Filter tiny clusters, sort by mean score
        significant = [c for c in clusters if len(c) >= MIN_ZONE_FEATURE_COUNT]
        # If no cluster meets minimum, include single-feature ones (don't lose all data)
        if not significant:
            significant = clusters

        significant_sorted = sorted(
            significant,
            key=lambda c: sum(f.risk_score for f in c) / len(c),
            reverse=True,
        )

        for rank, cluster in enumerate(significant_sorted[:MAX_PRIORITY_ZONES], start=1):
            zone = _build_zone(cluster, rank)
            priority_zones.append(zone)

    highest_level: RiskLevel = (
        _highest_risk([z.risk_level for z in priority_zones])
        if priority_zones
        else risk_result.summary.overall_risk_level
    )
    highest_score = (
        max(z.risk_score for z in priority_zones)
        if priority_zones
        else risk_result.summary.overall_risk_score
    )

    # Enrich agent context with priority zone data for Nemotron (Phase 4)
    agent_context = dict(risk_result.agent_context)
    agent_context["priority_zones"] = [
        {
            "zone_id": z.zone_id,
            "priority_rank": z.priority_rank,
            "risk_level": z.risk_level,
            "risk_score": z.risk_score,
            "feature_count": z.feature_count,
            "temperature_mean_c": z.temperature_mean_c,
            "temperature_max_c": z.temperature_max_c,
            "centroid": z.centroid,
            "reasons": z.reasons,
            "recommended_actions": z.recommended_actions,
        }
        for z in priority_zones
    ]
    agent_context["government_actions"] = (
        get_recommended_actions(highest_level)
    )

    logger.info(
        "Priority engine: complete | zones=%d | highest=%s | score=%d",
        len(priority_zones),
        highest_level,
        highest_score,
    )

    return PriorityAnalysisResult(
        city=risk_result.city,
        date=risk_result.date,
        activity_id=risk_result.activity_id,
        data_mode=risk_result.data_mode,
        priority_zones=priority_zones,
        total_high_extreme_features=total_high_extreme,
        highest_risk_level=highest_level,
        highest_risk_score=highest_score,
        agent_context=agent_context,
        data_limitations=risk_result.data_limitations,
    )
