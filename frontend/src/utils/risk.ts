import type { RiskLevel } from '../types';

export const RISK_COLORS: Record<RiskLevel, string> = {
  LOW:      '#60a5fa', // blue-400
  MODERATE: '#fbbf24', // amber-400
  HIGH:     '#f97316', // orange-500
  EXTREME:  '#dc2626', // red-600
};

export const RISK_BADGE_CLASS: Record<RiskLevel, string> = {
  LOW:      'risk-badge-low',
  MODERATE: 'risk-badge-moderate',
  HIGH:     'risk-badge-high',
  EXTREME:  'risk-badge-extreme',
};

export const RISK_BG_CLASS: Record<RiskLevel, string> = {
  LOW:      'bg-blue-900/30 border-blue-700',
  MODERATE: 'bg-yellow-900/30 border-yellow-700',
  HIGH:     'bg-orange-900/30 border-orange-700',
  EXTREME:  'bg-red-900/30 border-red-700',
};

export function riskScoreGradient(score: number): string {
  if (score >= 75) return 'text-red-400';
  if (score >= 50) return 'text-orange-400';
  if (score >= 25) return 'text-yellow-400';
  return 'text-blue-400';
}

/** Map temperature (°C) to a MapLibre fill color expression value */
export function tempToColor(temp: number): string {
  if (temp >= 40) return '#dc2626';
  if (temp >= 35) return '#f97316';
  if (temp >= 30) return '#fbbf24';
  return '#60a5fa';
}

export function formatTemp(c: number, unit: 'C' | 'F' = 'C'): string {
  if (unit === 'F') return `${((c * 9) / 5 + 32).toFixed(1)}°F`;
  return `${c.toFixed(1)}°C`;
}
