import { X, Thermometer, MapPin, AlertTriangle, Info } from 'lucide-react';
import type { PriorityZone } from '../types';
import { RISK_BADGE_CLASS, RISK_BG_CLASS, riskScoreGradient } from '../utils/risk';

interface ZoneDetailPanelProps {
  zone: PriorityZone;
  onClose: () => void;
  onAskAI: (zone: PriorityZone) => void;
}

export function ZoneDetailPanel({ zone, onClose, onAskAI }: ZoneDetailPanelProps) {
  return (
    <div className={`card border ${RISK_BG_CLASS[zone.risk_level]} flex flex-col gap-4`}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <MapPin size={14} className="text-gray-400" />
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
          className="text-gray-500 hover:text-gray-300 transition-colors"
          aria-label="Close zone detail"
        >
          <X size={16} />
        </button>
      </div>

      {/* Risk Score */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
            Risk Score
          </p>
          <p className={`text-3xl font-bold font-mono ${riskScoreGradient(zone.risk_score)}`}>
            {zone.risk_score}
            <span className="text-sm text-gray-500 font-normal"> / 100</span>
          </p>
          <p className="text-xs text-gray-600 mt-0.5">CIVICHEAT Decision-Support Score</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Tiles</p>
          <p className="text-xl font-bold text-white">{zone.feature_count}</p>
        </div>
      </div>

      {/* Temperature */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Mean', value: zone.temperature_mean_c },
          { label: 'Peak', value: zone.temperature_max_c },
          { label: 'Min',  value: zone.temperature_min_c },
        ].map(({ label, value }) => (
          <div key={label} className="bg-gov-900/50 rounded p-2 text-center">
            <Thermometer size={12} className="text-gray-500 mx-auto mb-0.5" />
            <p className="text-xs text-gray-500">{label}</p>
            <p className="text-sm font-bold text-white font-mono">{value.toFixed(1)}°C</p>
          </div>
        ))}
      </div>

      {/* Evidence */}
      <div>
        <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-1.5 flex items-center gap-1">
          <Info size={11} /> Evidence
        </p>
        <ul className="space-y-1">
          {zone.reasons.map((r, i) => (
            <li key={i} className="text-xs text-gray-300 flex items-start gap-1.5">
              <span className="text-gray-600 mt-0.5">•</span>
              <span>{r}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Recommendations */}
      <div>
        <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-1.5 flex items-center gap-1">
          <AlertTriangle size={11} /> Recommended Actions
        </p>
        <ul className="space-y-1">
          {zone.recommended_actions.map((a, i) => (
            <li key={i} className="text-xs text-gray-200 flex items-start gap-1.5">
              <span className="text-blue-500 font-bold mt-0.5">{i + 1}.</span>
              <span>{a}</span>
            </li>
          ))}
        </ul>
        {zone.action_rationale && (
          <p className="text-xs text-gray-500 mt-2 italic">{zone.action_rationale}</p>
        )}
      </div>

      {/* Ask AI */}
      <button
        onClick={() => onAskAI(zone)}
        className="btn-primary text-sm flex items-center justify-center gap-2 mt-1"
      >
        <span>⚡</span>
        Ask AI Why
      </button>
    </div>
  );
}
