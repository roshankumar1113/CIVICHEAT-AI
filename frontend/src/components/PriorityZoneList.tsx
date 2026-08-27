/**
 * CIVICHEAT priority zone list. §7
 *
 * Ordered explicitly by the backend's `priority_rank` so the display order is
 * the ranking the priority engine produced, never incidental array order.
 */
import { ChevronRight, MapPin } from 'lucide-react';
import type { PriorityZone } from '../types';
import { RISK_BADGE_CLASS, riskScoreGradient } from '../utils/risk';

interface PriorityZoneListProps {
  zones: PriorityZone[];
  selectedZoneId: string | null;
  onSelect: (zone: PriorityZone) => void;
}

export function PriorityZoneList({ zones, selectedZoneId, onSelect }: PriorityZoneListProps) {
  if (zones.length === 0) {
    return (
      <div className="card">
        <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">
          Priority Zones
        </h2>
        <p className="text-xs text-gray-500">No high-priority zones detected.</p>
        <p className="text-xs text-gray-600 mt-1 leading-tight">
          No tile reached the HIGH risk threshold, so the priority engine produced no zones.
        </p>
      </div>
    );
  }

  const ranked = [...zones].sort((a, b) => a.priority_rank - b.priority_rank);

  return (
    <div className="card">
      <div className="flex items-baseline justify-between mb-2.5">
        <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest">
          Priority Zones
        </h2>
        <span className="text-xs text-gray-600 font-mono">{ranked.length} ranked</span>
      </div>

      <ol className="space-y-2">
        {ranked.map((zone) => {
          const isSelected = selectedZoneId === zone.zone_id;
          return (
            <li key={zone.zone_id}>
              <button
                onClick={() => onSelect(zone)}
                aria-pressed={isSelected}
                aria-label={`Priority rank ${zone.priority_rank}, zone ${zone.zone_id}, ${zone.risk_level} risk, score ${zone.risk_score} of 100. View details.`}
                className={`w-full text-left rounded p-2.5 border transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                  isSelected
                    ? 'bg-blue-900/30 border-blue-600'
                    : 'bg-gov-900/40 border-gov-600 hover:border-gov-500 hover:bg-gov-700/30'
                }`}
              >
                <div className="flex items-center justify-between mb-1 gap-2">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5 min-w-0">
                    <span
                      className="bg-gov-700 text-gray-300 rounded px-1.5 py-0.5 font-mono text-[10px] flex-shrink-0"
                      title={`Priority rank ${zone.priority_rank}`}
                    >
                      #{zone.priority_rank}
                    </span>
                    <MapPin size={10} className="text-gray-400 flex-shrink-0" aria-hidden="true" />
                    <span className="truncate">{zone.zone_id}</span>
                  </span>
                  <span className={`${RISK_BADGE_CLASS[zone.risk_level]} flex-shrink-0`}>
                    {zone.risk_level}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">{zone.feature_count} tiles</span>
                  <span className={`text-xs font-mono font-bold ${riskScoreGradient(zone.risk_score)}`}>
                    {zone.risk_score}
                    <span className="text-gray-600 font-normal">/100</span>
                  </span>
                </div>

                <div className="text-xs text-gray-500 mt-0.5 font-mono">
                  {zone.temperature_mean_c.toFixed(1)}°C mean · {zone.temperature_max_c.toFixed(1)}°C peak
                </div>

                <div
                  className={`mt-1.5 pt-1.5 border-t flex items-center justify-between text-[10px] font-bold uppercase tracking-widest ${
                    isSelected
                      ? 'border-blue-800/60 text-blue-300'
                      : 'border-gov-700 text-gray-500'
                  }`}
                >
                  <span>{isSelected ? 'Details open' : 'View details'}</span>
                  <ChevronRight size={11} aria-hidden="true" />
                </div>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
