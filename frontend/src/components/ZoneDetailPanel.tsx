/**
 * CIVICHEAT zone detail panel. §8
 *
 * Attribution matters here. The recommended actions on this panel come from the
 * deterministic CIVICHEAT rule engine, so they are labelled as such. The
 * "AI-generated decision support" label sits on ASK CIVICHEAT WHY — the one
 * affordance that actually produces model output.
 */
import { AlertTriangle, Info, MapPin, Thermometer, X, Zap } from 'lucide-react';
import type { PriorityZone } from '../types';
import { RISK_BADGE_CLASS, RISK_BG_CLASS, riskScoreGradient } from '../utils/risk';

interface ZoneDetailPanelProps {
  zone: PriorityZone;
  onClose: () => void;
  onAskAI: (zone: PriorityZone) => void;
  /** Disabled while another agent request is already running. */
  askDisabled?: boolean;
}

export function ZoneDetailPanel({ zone, onClose, onAskAI, askDisabled = false }: ZoneDetailPanelProps) {
  return (
    <section
      className={`card border ${RISK_BG_CLASS[zone.risk_level]} flex flex-col gap-4`}
      aria-label={`Detail for zone ${zone.zone_id}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <MapPin size={14} className="text-gray-400 flex-shrink-0" aria-hidden="true" />
            <span className="text-sm font-bold text-white">{zone.zone_id}</span>
            <span className="text-gray-500">·</span>
            <span className="text-xs text-gray-400">Priority #{zone.priority_rank}</span>
          </div>
          <span className={`mt-1 inline-block ${RISK_BADGE_CLASS[zone.risk_level]}`}>
            {zone.risk_level}
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-300 transition-colors flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded px-1 py-0.5 flex-shrink-0"
          aria-label="Close zone detail"
        >
          <X size={13} aria-hidden="true" />
          Close
        </button>
      </div>

      {/* Risk Score */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Risk Score</p>
          <p className={`text-3xl font-bold font-mono ${riskScoreGradient(zone.risk_score)}`}>
            {zone.risk_score}
            <span className="text-sm text-gray-500 font-normal"> / 100</span>
          </p>
          <p className="text-xs text-gray-600 mt-0.5">
            Application-defined decision-support score.
          </p>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Tiles</p>
          <p className="text-xl font-bold text-white font-mono">{zone.feature_count}</p>
        </div>
      </div>

      {/* Temperature */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Mean', value: zone.temperature_mean_c },
          { label: 'Peak', value: zone.temperature_max_c },
          { label: 'Min', value: zone.temperature_min_c },
        ].map(({ label, value }) => (
          <div key={label} className="bg-gov-900/50 rounded p-2 text-center">
            <Thermometer size={12} className="text-gray-500 mx-auto mb-0.5" aria-hidden="true" />
            <p className="text-xs text-gray-500">{label}</p>
            <p className="text-sm font-bold text-white font-mono">{value.toFixed(1)}°C</p>
          </div>
        ))}
      </div>

      {/* Evidence */}
      <div>
        <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-1.5 flex items-center gap-1">
          <Info size={11} aria-hidden="true" /> Evidence
        </p>
        <ul className="space-y-1">
          {zone.reasons.map((r, i) => (
            <li key={i} className="text-xs text-gray-300 flex items-start gap-1.5">
              <span className="text-gray-600 mt-0.5" aria-hidden="true">•</span>
              <span>{r}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Recommendations — deterministic, and labelled as such */}
      <div>
        <div className="flex items-baseline justify-between gap-2 mb-1.5">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-wide flex items-center gap-1">
            <AlertTriangle size={11} aria-hidden="true" /> Recommended Actions
          </p>
          <span className="text-[10px] text-gray-600 font-mono uppercase tracking-wider flex-shrink-0">
            Rule engine
          </span>
        </div>
        <ol className="space-y-1">
          {zone.recommended_actions.map((a, i) => (
            <li key={i} className="text-xs text-gray-200 flex items-start gap-1.5">
              <span className="text-blue-500 font-bold mt-0.5 font-mono" aria-hidden="true">
                {i + 1}.
              </span>
              <span>{a}</span>
            </li>
          ))}
        </ol>
        {zone.action_rationale && (
          <p className="text-xs text-gray-500 mt-2 leading-tight">{zone.action_rationale}</p>
        )}
        <p className="text-xs text-gray-600 mt-1.5 leading-tight">
          Produced by CIVICHEAT risk rules from this zone's classification — not model-generated.
        </p>
      </div>

      {/* Ask CIVICHEAT — the actual AI path */}
      <div className="border-t border-gov-700 pt-3">
        <button
          onClick={() => onAskAI(zone)}
          disabled={askDisabled}
          className="btn-primary text-sm w-full flex items-center justify-center gap-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
          aria-label={`Ask CIVICHEAT why zone ${zone.zone_id} is prioritised`}
        >
          <Zap size={13} aria-hidden="true" />
          Ask CIVICHEAT Why
        </button>
        <p className="text-xs text-gray-600 mt-1.5 text-center">
          AI-generated decision support. Requires official review before action.
        </p>
      </div>
    </section>
  );
}
