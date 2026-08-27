import type { PriorityAnalysisResult, RiskLevel } from '../types';

/**
 * Typed accessors for `PriorityAnalysisResult.agent_context`.
 *
 * The backend types agent_context as an open map because its shape is driven by
 * what the Nemotron tools need. These readers narrow the parts the dashboard
 * displays, so no component has to reach into it with a cast.
 *
 * Every reader returns null when the field is genuinely absent. Callers render
 * an em dash in that case — the dashboard never substitutes a placeholder
 * number for a value the backend did not provide.
 */

export interface TemperatureSummary {
  mean_c: number;
  min_c: number;
  max_c: number;
  std_dev: number;
  percentiles: number[];
}

export interface RiskSummary {
  overall_level: RiskLevel;
  overall_score: number;
  feature_counts: Record<RiskLevel, number>;
  total_features: number;
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

export function temperatureSummary(
  result: PriorityAnalysisResult | null | undefined,
): TemperatureSummary | null {
  const raw = result?.agent_context?.['temperature_summary'];
  if (!isRecord(raw)) return null;

  const mean = num(raw['mean_c']);
  const min = num(raw['min_c']);
  const max = num(raw['max_c']);
  if (mean === null || min === null || max === null) return null;

  return {
    mean_c: mean,
    min_c: min,
    max_c: max,
    std_dev: num(raw['std_dev']) ?? 0,
    percentiles: Array.isArray(raw['percentiles'])
      ? raw['percentiles'].filter((p): p is number => typeof p === 'number')
      : [],
  };
}

const ZERO_COUNTS: Record<RiskLevel, number> = { LOW: 0, MODERATE: 0, HIGH: 0, EXTREME: 0 };

export function riskSummary(
  result: PriorityAnalysisResult | null | undefined,
): RiskSummary | null {
  const raw = result?.agent_context?.['risk_summary'];
  if (!isRecord(raw)) return null;

  const total = num(raw['total_features']);
  const score = num(raw['overall_score']);
  if (total === null || score === null) return null;

  const counts = { ...ZERO_COUNTS };
  const rawCounts = raw['feature_counts'];
  if (isRecord(rawCounts)) {
    (Object.keys(counts) as RiskLevel[]).forEach((level) => {
      counts[level] = num(rawCounts[level]) ?? 0;
    });
  }

  return {
    overall_level: (raw['overall_level'] as RiskLevel) ?? 'LOW',
    overall_score: score,
    feature_counts: counts,
    total_features: total,
  };
}

/** Deterministic government actions the risk engine produced for this analysis. */
export function governmentActions(
  result: PriorityAnalysisResult | null | undefined,
): string[] {
  const raw = result?.agent_context?.['government_actions'];
  return Array.isArray(raw) ? raw.filter((a): a is string => typeof a === 'string') : [];
}
