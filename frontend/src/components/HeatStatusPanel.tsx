import { Thermometer, MapPin, AlertTriangle, Cpu } from 'lucide-react';
import type { PriorityAnalysisResult } from '../types';
import { RISK_BADGE_CLASS, riskScoreGradient } from '../utils/risk';

interface HeatStatusPanelProps {
  result: PriorityAnalysisResult | null;
  loading: boolean;
}

export function HeatStatusPanel({ result, loading }: HeatStatusPanelProps) {
  return (
    <div className="card space-y-3">
      <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest">
        Heat Status
      </h2>

      {loading && (
        <p className="text-xs text-blue-400 animate-pulse">
          Analyzing temperature intelligence…
        </p>
      )}

      {!loading && !result && (
        <p className="text-xs text-gray-600">No data — run analysis</p>
      )}

      {result && (
        <>
          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <Thermometer size={11} /> Mean Temp
            </span>
            <span className="text-sm font-bold font-mono text-white">
              {result.agent_context?.temperature_summary
                ? (result.agent_context.temperature_summary as { mean_c: number }).mean_c.toFixed(2)
                : '—'}°C
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <Thermometer size={11} /> Peak Temp
            </span>
            <span className="text-sm font-bold font-mono text-white">
              {result.agent_context?.temperature_summary
                ? (result.agent_context.temperature_summary as { max_c: number }).max_c.toFixed(2)
                : '—'}°C
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-400">Overall Risk</span>
            <span className={RISK_BADGE_CLASS[result.highest_risk_level]}>
              {result.highest_risk_level}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-400">Risk Score</span>
            <span className={`text-sm font-bold font-mono ${riskScoreGradient(result.highest_risk_score)}`}>
              {result.highest_risk_score}
              <span className="text-gray-600 text-xs font-normal"> /100</span>
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <MapPin size={11} /> Priority Zones
            </span>
            <span className="text-white font-bold">{result.priority_zones.length}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <AlertTriangle size={11} /> High/Extreme Tiles
            </span>
            <span className="text-orange-400 font-bold font-mono">
              {result.total_high_extreme_features}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <Cpu size={11} /> AI Agent
            </span>
            <span className="text-green-400 text-xs font-bold uppercase">Ready</span>
          </div>

          <div className="pt-1 border-t border-gov-600">
            <p className="text-xs text-gray-600 leading-tight">
              {result.data_mode === 'DEMO'
                ? '⚠ Demo data — FortyGuard API not configured'
                : '● Live FortyGuard data'}
            </p>
          </div>
        </>
      )}
    </div>
  );
}
