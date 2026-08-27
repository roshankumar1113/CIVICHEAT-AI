/**
 * CIVICHEAT HeatWatch Panel — Phase 4.5 (Continuous Reassessment)
 *
 * States:
 *   idle    → "NEXT REASSESSMENT / {interval} min / [REASSESS NOW]"
 *   loading → "Analyzing new FortyGuard data…"
 *   error   → retry
 *   done    → HEATWATCH UPDATE (previous vs current comparison) + optional
 *             Nemotron reassessment decision
 *
 * Every value shown is taken directly from POST /api/reassessment/run.
 * No fabricated numbers — if the data did not change, the panel says so.
 */
import {
  RefreshCw, Clock, TrendingUp, TrendingDown, Minus,
  CheckCircle, AlertTriangle, Loader2, X, Zap, ShieldCheck,
} from 'lucide-react';
import type { ReactNode } from 'react';
import type { ReassessmentResponse } from '../types';
import type { HeatWatchStatus } from '../hooks/useReassessment';
import { RISK_BADGE_CLASS, riskScoreGradient } from '../utils/risk';

interface HeatWatchPanelProps {
  response: ReassessmentResponse | null;
  status: HeatWatchStatus;
  error?: string | null;
  /** Cadence shown before/after a run — the CIVICHEAT default reassessment interval. */
  intervalMinutes?: number;
  onReassess: () => void;
  onClose?: () => void;
}

const urgencyColor: Record<string, string> = {
  LOW: 'text-blue-400',
  MEDIUM: 'text-yellow-400',
  HIGH: 'text-red-400',
};

function PanelShell({
  children,
  onClose,
}: {
  children: ReactNode;
  onClose?: () => void;
}) {
  return (
    <div className="card border border-blue-800 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck size={14} className="text-blue-400" />
          <span className="text-sm font-bold text-blue-300 uppercase tracking-wide">
            HeatWatch
          </span>
        </div>
        {onClose && (
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300">
            <X size={14} />
          </button>
        )}
      </div>
      {children}
    </div>
  );
}

export function HeatWatchPanel({
  response,
  status,
  error,
  intervalMinutes = 60,
  onReassess,
  onClose,
}: HeatWatchPanelProps) {
  // ── Loading ────────────────────────────────────────────────────────────────
  if (status === 'loading') {
    return (
      <PanelShell onClose={onClose}>
        <p className="text-xs text-blue-400 animate-pulse font-mono">
          Analyzing new FortyGuard data…
        </p>
        <div className="space-y-1.5">
          {[
            'Retrieving new FortyGuard data',
            'Recalculating heat risk',
            'Comparing with previous analysis',
          ].map((step) => (
            <div key={step} className="flex items-center gap-2 text-xs text-gray-500">
              <Loader2 size={10} className="animate-spin text-blue-600" />
              <span>{step}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-600">
          FortyGuard → Risk Engine → Comparison → Nemotron
        </p>
      </PanelShell>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────────
  if (status === 'error') {
    return (
      <PanelShell onClose={onClose}>
        <div className="bg-red-900/30 border border-red-700 rounded p-2">
          <p className="text-xs text-red-300">⚠ {error || 'Reassessment failed — try again'}</p>
        </div>
        <button
          onClick={onReassess}
          className="btn-primary w-full flex items-center justify-center gap-2 text-sm"
        >
          <RefreshCw size={13} /> Reassess Now
        </button>
      </PanelShell>
    );
  }

  // ── Idle (no run yet) ──────────────────────────────────────────────────────
  if (status === 'idle' || !response) {
    return (
      <PanelShell onClose={onClose}>
        <div className="bg-gov-900/50 rounded p-3 space-y-1">
          <p className="text-xs font-bold text-gray-500 uppercase tracking-widest flex items-center gap-1">
            <Clock size={11} /> Next Reassessment
          </p>
          <p className="text-2xl font-bold text-white font-mono">
            {intervalMinutes} <span className="text-sm text-gray-500 font-normal">min</span>
          </p>
        </div>
        <button
          onClick={onReassess}
          className="btn-primary w-full flex items-center justify-center gap-2 text-sm"
        >
          <RefreshCw size={13} /> Reassess Now
        </button>
        <p className="text-xs text-gray-600 leading-tight">
          Runs a fresh FortyGuard analysis and compares it against the last stored
          assessment. Nemotron is only invoked if a meaningful change is detected.
        </p>
      </PanelShell>
    );
  }

  // ── Done ────────────────────────────────────────────────────────────────
  const { comparison, status: reStatus, previous_snapshot, nemotron_decision, nemotron_fallback } = response;

  // First run — baseline captured, nothing to compare against yet.
  if (previous_snapshot === null) {
    return (
      <PanelShell onClose={onClose}>
        <div className="bg-gov-900/50 rounded p-3 space-y-1">
          <p className="text-xs font-bold text-gray-500 uppercase tracking-widest">
            Baseline Captured
          </p>
          <p className="text-xs text-gray-300">{reStatus.message}</p>
          <div className="flex items-center justify-between pt-1">
            <span className="text-xs text-gray-400">Current Risk</span>
            <span className={`text-sm font-bold font-mono ${riskScoreGradient(comparison.current_risk_score)}`}>
              {comparison.current_risk_score}<span className="text-gray-600 text-xs font-normal">/100</span>
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">Priority Zones</span>
            <span className="text-sm font-bold text-white font-mono">{comparison.current_zone_count}</span>
          </div>
        </div>
        <button
          onClick={onReassess}
          className="btn-primary w-full flex items-center justify-center gap-2 text-sm"
        >
          <RefreshCw size={13} /> Reassess Again
        </button>
        <p className="text-xs text-gray-600 leading-tight">
          Run again to compare against this baseline.
        </p>
      </PanelShell>
    );
  }

  const change = comparison.risk_score_change;
  const meaningful = comparison.meaningful_change;
  const ChangeIcon = change > 0 ? TrendingUp : change < 0 ? TrendingDown : Minus;
  const changeColor =
    change > 0 ? 'text-red-400' : change < 0 ? 'text-blue-400' : 'text-gray-500';
  const changeArrow = change > 0 ? '↑' : change < 0 ? '↓' : '→';

  // Tool-activity checklist — derived from what actually happened server-side.
  const activity: string[] = [
    'Retrieved new FortyGuard data',
    'Recalculated heat risk',
    'Compared previous analysis',
    meaningful ? 'Detected significant change' : 'No significant change detected',
  ];
  if (nemotron_decision) {
    activity.push(
      nemotron_fallback ? 'Reassessed response (deterministic fallback)' : 'Nemotron reassessed response',
    );
  }

  const significantZones = comparison.changed_zones.filter(
    (z) => z.change_type === 'new' || z.change_type === 'removed' || z.change_type === 'rank_shifted',
  );

  return (
    <PanelShell onClose={onClose}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-gray-500 uppercase tracking-widest">
          HeatWatch Update
        </span>
        <span className="text-xs bg-gov-700 text-gray-400 border border-gov-500 px-2 py-0.5 rounded font-mono uppercase">
          {response.data_mode}
        </span>
      </div>

      {/* ── Comparison card ─────────────────────────────────────────────── */}
      <div className="bg-gov-900/60 rounded-lg border border-gov-600 p-3 space-y-3">
        {/* Risk */}
        <div className="grid grid-cols-2 gap-2">
          <div className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Previous</p>
            <p className={`text-2xl font-bold font-mono ${riskScoreGradient(comparison.previous_risk_score)}`}>
              {comparison.previous_risk_score}
            </p>
            <span className={RISK_BADGE_CLASS[comparison.previous_risk_level]}>
              {comparison.previous_risk_level}
            </span>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Current</p>
            <p className={`text-2xl font-bold font-mono ${riskScoreGradient(comparison.current_risk_score)}`}>
              {comparison.current_risk_score}
            </p>
            <span className={RISK_BADGE_CLASS[comparison.current_risk_level]}>
              {comparison.current_risk_level}
            </span>
          </div>
        </div>

        {/* Change */}
        <div className={`flex items-center justify-center gap-1.5 text-sm font-bold font-mono ${changeColor}`}>
          <ChangeIcon size={14} />
          <span>
            {changeArrow} {change > 0 ? '+' : ''}{change} pts
          </span>
        </div>

        {/* Zones */}
        <div className="flex items-center justify-between border-t border-gov-700 pt-2">
          <span className="text-xs text-gray-400">Priority Zones</span>
          <span className="text-sm font-bold text-white font-mono">
            {comparison.previous_zone_count} → {comparison.current_zone_count}
          </span>
        </div>

        {/* Mean temperature */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-400">Mean Temp Δ</span>
          <span className="text-sm font-bold text-white font-mono">
            {comparison.mean_temperature_change_c > 0 ? '+' : ''}
            {comparison.mean_temperature_change_c.toFixed(1)}°C
          </span>
        </div>

        {/* Status line — exact CIVICHEAT reassessment verdict. §13 */}
        <div
          className={`rounded px-2 py-1.5 text-xs font-bold uppercase tracking-wide flex items-center justify-center gap-1.5 ${
            meaningful
              ? 'bg-orange-900/40 text-orange-300 border border-orange-700'
              : 'bg-blue-900/30 text-blue-300 border border-blue-800'
          }`}
        >
          {meaningful ? <AlertTriangle size={12} aria-hidden="true" /> : <CheckCircle size={12} aria-hidden="true" />}
          {meaningful ? 'Significant Change Detected' : 'No Significant Change'}
        </div>
      </div>

      {/* Nemotron intentionally skipped — the conditional-invocation story. §13 */}
      {!meaningful && (
        <div className="bg-gov-900/50 rounded-lg border border-gov-600 p-3 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gray-400 uppercase tracking-wide flex items-center gap-1">
              <Zap size={12} aria-hidden="true" /> Nemotron
            </span>
            <span className="text-xs bg-gov-700 text-gray-300 border border-gov-500 px-2 py-0.5 rounded font-mono">
              NOT REQUIRED
            </span>
          </div>
          <p className="text-xs text-gray-400 leading-snug">
            Current conditions do not meet the CIVICHEAT reassessment threshold.
          </p>
          <p className="text-[10px] text-gray-600 leading-snug">
            The model is only invoked when a meaningful change is detected — no inference call
            was made for this cycle.
          </p>
        </div>
      )}

      {/* ── Change reasons ──────────────────────────────────────────────── */}
      {comparison.change_reasons.length > 0 && (
        <div>
          <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-1.5">
            What Changed
          </p>
          <ul className="space-y-1">
            {comparison.change_reasons.map((r, i) => (
              <li key={i} className="text-xs text-gray-300 flex gap-1.5">
                <span className="text-gray-600 flex-shrink-0 mt-0.5">•</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Significant zone changes ────────────────────────────────────── */}
      {significantZones.length > 0 && (
        <div>
          <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-1.5">
            Zone Changes
          </p>
          <ul className="space-y-1">
            {significantZones.map((z) => (
              <li key={z.zone_id} className="text-xs text-gray-300 flex justify-between gap-2">
                <span className="font-mono text-white">{z.zone_id}</span>
                <span className="text-gray-500 uppercase">{z.change_type.replace('_', ' ')}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Tool activity ───────────────────────────────────────────────── */}
      <div>
        <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-1.5">
          Tool Activity
        </p>
        <div className="space-y-1">
          {activity.map((a) => (
            <div key={a} className="flex items-center gap-2 text-xs text-gray-400">
              <CheckCircle size={11} className="text-green-500 flex-shrink-0" />
              <span>{a}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Nemotron reassessment decision ──────────────────────────────── */}
      {nemotron_decision && (
        <div className="border-t border-gov-700 pt-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-blue-300 uppercase tracking-wide flex items-center gap-1">
              <Zap size={12} /> Nemotron Reassessment
            </span>
            {nemotron_fallback ? (
              <span className="text-xs bg-yellow-900 text-yellow-300 border border-yellow-700 px-2 py-0.5 rounded font-mono">
                FALLBACK
              </span>
            ) : (
              <span className="text-xs bg-green-900 text-green-300 border border-green-700 px-2 py-0.5 rounded font-mono">
                ● LIVE
              </span>
            )}
          </div>

          <div className="bg-gov-900/50 rounded p-2.5 space-y-1.5">
            <div>
              <span className="text-xs text-gray-500">Status</span>
              <p className="text-xs font-bold text-orange-300 uppercase tracking-wide">
                Update Recommended
              </p>
            </div>
            <div>
              <span className="text-xs text-gray-500">Reason</span>
              <p className="text-xs text-gray-200">{nemotron_decision.decision}</p>
            </div>
            {nemotron_decision.priority_zone && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">Changed Priority</span>
                <span className="text-xs font-bold text-white font-mono">
                  {nemotron_decision.priority_zone}
                </span>
              </div>
            )}
          </div>

          {nemotron_decision.recommended_actions.length > 0 && (
            <div>
              <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-1.5">
                Recommended Changes
              </p>
              <ol className="space-y-1.5">
                {nemotron_decision.recommended_actions.map((a, i) => (
                  <li key={i} className="text-xs">
                    <div className="flex items-start gap-2">
                      <span className="text-blue-400 font-bold font-mono w-4 flex-shrink-0">{i + 1}.</span>
                      <div className="flex-1">
                        <span className="text-gray-200">{a.action}</span>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className={`font-bold uppercase ${urgencyColor[a.urgency] || 'text-gray-500'}`}>
                            {a.urgency}
                          </span>
                          <span className="text-gray-600">{a.reason}</span>
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}

      {/* ── Re-run ──────────────────────────────────────────────────────── */}
      <button
        onClick={onReassess}
        className="btn-secondary w-full flex items-center justify-center gap-2 text-sm"
      >
        <RefreshCw size={13} /> Reassess Again
      </button>

      {/* Disclaimer */}
      <p className="text-xs text-gray-700 leading-tight border-t border-gov-700 pt-2">
        {comparison.disclaimer}
      </p>
    </PanelShell>
  );
}
