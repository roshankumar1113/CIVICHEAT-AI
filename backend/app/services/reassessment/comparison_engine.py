"""
CIVICHEAT Comparison Engine.

Deterministic comparison of two analysis snapshots.
No LLM involved — pure data comparison.
"""
from __future__ import annotations
import logging
from app.services.reassessment.comparison_models import (
    AnalysisSnapshot,
    ChangeThresholds,
    ComparisonResult,
    ZoneChange,
)

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLDS = ChangeThresholds()


def compare_snapshots(
    previous: AnalysisSnapshot,
    current: AnalysisSnapshot,
    thresholds: ChangeThresholds = _DEFAULT_THRESHOLDS,
) -> ComparisonResult:
    """
    Compare two analysis snapshots and return a structured ComparisonResult.
    All arithmetic is on real data — nothing fabricated.
    """
    # Temperature deltas
    mean_delta = round(current.mean_temperature_c - previous.mean_temperature_c, 3)
    max_delta  = round(current.max_temperature_c  - previous.max_temperature_c,  3)

    # Risk deltas
    score_delta = current.overall_risk_score - previous.overall_risk_score
    zone_delta  = current.priority_zone_count - previous.priority_zone_count

    # Zone-level changes
    prev_zones = {z["zone_id"]: z for z in previous.priority_zones}
    curr_zones = {z["zone_id"]: z for z in current.priority_zones}

    changed_zones: list[ZoneChange] = []

    # New zones
    for zid, z in curr_zones.items():
        if zid not in prev_zones:
            changed_zones.append(ZoneChange(
                zone_id=zid,
                previous_rank=None,
                current_rank=z.get("priority_rank"),
                previous_score=None,
                current_score=z.get("risk_score"),
                change_type="new",
            ))

    # Removed zones
    for zid, z in prev_zones.items():
        if zid not in curr_zones:
            changed_zones.append(ZoneChange(
                zone_id=zid,
                previous_rank=z.get("priority_rank"),
                current_rank=None,
                previous_score=z.get("risk_score"),
                current_score=None,
                change_type="removed",
            ))

    # Existing zones — check rank/score shifts
    for zid in set(prev_zones) & set(curr_zones):
        pz = prev_zones[zid]
        cz = curr_zones[zid]
        prev_rank  = pz.get("priority_rank", 0)
        curr_rank  = cz.get("priority_rank", 0)
        prev_score = pz.get("risk_score", 0)
        curr_score = cz.get("risk_score", 0)
        rank_shift = abs(curr_rank - prev_rank)

        if rank_shift >= thresholds.zone_rank_shift:
            change_type = "rank_shifted"
        elif prev_score != curr_score:
            change_type = "score_changed"
        else:
            change_type = "unchanged"

        changed_zones.append(ZoneChange(
            zone_id=zid,
            previous_rank=prev_rank,
            current_rank=curr_rank,
            previous_score=prev_score,
            current_score=curr_score,
            change_type=change_type,
        ))

    # Meaningful-change detection
    change_reasons: list[str] = []

    if abs(score_delta) >= thresholds.risk_score_delta:
        direction = "increased" if score_delta > 0 else "decreased"
        change_reasons.append(
            f"Risk score {direction} by {abs(score_delta)} points "
            f"({previous.overall_risk_score} → {current.overall_risk_score})."
        )

    if abs(mean_delta) >= thresholds.mean_temperature_delta_c:
        direction = "increased" if mean_delta > 0 else "decreased"
        change_reasons.append(
            f"Mean temperature {direction} by {abs(mean_delta):.1f}°C "
            f"({previous.mean_temperature_c:.2f} → {current.mean_temperature_c:.2f}°C)."
        )

    if thresholds.zone_count_change and zone_delta != 0:
        direction = "increased" if zone_delta > 0 else "decreased"
        change_reasons.append(
            f"Priority zone count {direction} "
            f"({previous.priority_zone_count} → {current.priority_zone_count})."
        )

    significant_zone_changes = [
        z for z in changed_zones
        if z.change_type in ("new", "removed", "rank_shifted")
    ]
    if significant_zone_changes and not any("zone count" in r for r in change_reasons):
        change_reasons.append(
            f"{len(significant_zone_changes)} priority zone(s) changed significantly."
        )

    meaningful_change = len(change_reasons) > 0

    logger.info(
        "Comparison: score_delta=%+d | mean_delta=%+.2f°C | zone_delta=%+d | "
        "meaningful=%s | reasons=%d",
        score_delta, mean_delta, zone_delta, meaningful_change, len(change_reasons),
    )

    return ComparisonResult(
        previous_snapshot_id=previous.analysis_id,
        current_snapshot_id=current.analysis_id,
        mean_temperature_change_c=mean_delta,
        max_temperature_change_c=max_delta,
        risk_score_change=score_delta,
        previous_risk_score=previous.overall_risk_score,
        current_risk_score=current.overall_risk_score,
        previous_risk_level=previous.overall_risk_level,
        current_risk_level=current.overall_risk_level,
        previous_zone_count=previous.priority_zone_count,
        current_zone_count=current.priority_zone_count,
        priority_zone_change=zone_delta,
        changed_zones=changed_zones,
        meaningful_change=meaningful_change,
        change_reasons=change_reasons,
        thresholds_used=thresholds,
    )
