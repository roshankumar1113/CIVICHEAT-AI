import { MapPin } from 'lucide-react';
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
        <p className="text-xs text-gray-600">No high-priority zones detected.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-3">
        Priority Zones
      </h2>
      <div className="space-y-2">
        {zones.map((zone) => (
          <button
            key={zone.zone_id}
            onClick={() => onSelect(zone)}
            className={`w-full text-left rounded p-2.5 border transition-colors duration-150 ${
              selectedZoneId === zone.zone_id
                ? 'bg-blue-900/30 border-blue-600'
                : 'bg-gov-900/40 border-gov-600 hover:border-gov-500 hover:bg-gov-700/30'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-bold text-white flex items-center gap-1">
                <MapPin size={10} className="text-gray-400" />
                {zone.zone_id}
              </span>
              <span className={RISK_BADGE_CLASS[zone.risk_level]}>
                {zone.risk_level}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">{zone.feature_count} tiles</span>
              <span className={`text-xs font-mono font-bold ${riskScoreGradient(zone.risk_score)}`}>
                {zone.risk_score}/100
              </span>
            </div>
            <div className="text-xs text-gray-500 mt-0.5 font-mono">
              {zone.temperature_mean_c.toFixed(1)}°C mean · {zone.temperature_max_c.toFixed(1)}°C peak
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
