/**
 * CIVICHEAT map legend. §6
 *
 * Explains both encodings on the map: the absolute temperature/risk bands used
 * to colour tiles, and the three map layers. Tile counts and the observed range
 * come from the live analysis, so when every tile falls in a single band the
 * legend says exactly that rather than implying visual variation.
 */
import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { PriorityAnalysisResult, RiskLevel } from '../types';
import { RISK_COLORS } from '../utils/risk';
import { riskSummary, temperatureSummary } from '../utils/analysis';

interface LegendItem {
  level: RiskLevel;
  label: string;
  range: string;
}

const LEGEND_ITEMS: LegendItem[] = [
  { level: 'LOW', label: 'Low', range: '< 30°C' },
  { level: 'MODERATE', label: 'Moderate', range: '30 – 34.9°C' },
  { level: 'HIGH', label: 'High', range: '35 – 39.9°C' },
  { level: 'EXTREME', label: 'Extreme', range: '≥ 40°C' },
];

interface TemperatureLegendProps {
  result?: PriorityAnalysisResult | null;
}

export function TemperatureLegend({ result }: TemperatureLegendProps) {
  const [expanded, setExpanded] = useState(false);
  const risk = riskSummary(result);
  const temp = temperatureSummary(result);

  // Which bands actually contain tiles in this analysis.
  const occupied = risk
    ? LEGEND_ITEMS.filter((i) => risk.feature_counts[i.level] > 0)
    : [];
  const singleBand = occupied.length === 1 ? occupied[0] : null;

  return (
    <div className="bg-gov-800/95 border border-gov-600 rounded-lg text-xs backdrop-blur-sm max-w-[15rem]">
      <div className="px-3 pt-2.5 pb-2">
        <p className="font-bold text-gray-400 uppercase tracking-widest mb-2 text-[10px]">
          Risk Classification
        </p>
        <div className="space-y-1">
          {LEGEND_ITEMS.map((item) => {
            const count = risk?.feature_counts[item.level];
            return (
              <div key={item.level} className="flex items-center gap-2">
                <span
                  className="w-3 h-3 rounded-sm flex-shrink-0 border border-black/30"
                  style={{ backgroundColor: RISK_COLORS[item.level] }}
                  aria-hidden="true"
                />
                <span className="text-gray-300 flex-1">{item.label}</span>
                <span className="text-gray-600 font-mono text-[10px]">{item.range}</span>
                {typeof count === 'number' && (
                  <span
                    className={`font-mono text-[10px] w-8 text-right ${
                      count > 0 ? 'text-gray-300' : 'text-gray-700'
                    }`}
                    title={`${count} tile(s) classified ${item.level}`}
                  >
                    {count}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Honest note when the whole dataset sits in one band. */}
        {singleBand && temp && (
          <p className="text-[10px] text-gray-500 mt-2 leading-tight border-t border-gov-700 pt-1.5">
            All {risk?.total_features.toLocaleString()} tiles classified{' '}
            <span className="font-bold" style={{ color: RISK_COLORS[singleBand.level] }}>
              {singleBand.level}
            </span>{' '}
            ({temp.min_c.toFixed(2)}–{temp.max_c.toFixed(2)}°C). Uniform colour reflects a uniform
            observation, not missing detail.
          </p>
        )}
      </div>

      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-1.5 border-t border-gov-700 flex items-center justify-between text-[10px] text-gray-500 hover:text-gray-300 transition-colors"
        aria-expanded={expanded}
        aria-label={expanded ? 'Hide map layer details' : 'Show map layer details'}
      >
        <span className="uppercase tracking-widest font-bold">Map Layers</span>
        {expanded ? <ChevronUp size={11} aria-hidden="true" /> : <ChevronDown size={11} aria-hidden="true" />}
      </button>

      {expanded && (
        <div className="px-3 pb-2.5 pt-1 space-y-2 border-t border-gov-700/50">
          <div className="flex items-start gap-2">
            <span
              className="w-3 h-3 rounded-sm flex-shrink-0 mt-0.5 opacity-50"
              style={{ backgroundColor: RISK_COLORS.HIGH }}
              aria-hidden="true"
            />
            <div>
              <p className="text-gray-300 text-[10px] font-bold uppercase tracking-wide">Temperature</p>
              <p className="text-gray-500 text-[10px] leading-tight">
                Filled FortyGuard tiles, coloured by the bands above.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-2">
            <span
              className="w-3 h-3 flex-shrink-0 mt-0.5 border-2 border-dashed"
              style={{ borderColor: RISK_COLORS.HIGH }}
              aria-hidden="true"
            />
            <div>
              <p className="text-gray-300 text-[10px] font-bold uppercase tracking-wide">
                Priority Zones
              </p>
              <p className="text-gray-500 text-[10px] leading-tight">
                Dashed outline with rank label. Click to open zone detail.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-2">
            <span className="w-3 h-3 flex-shrink-0 mt-0.5 border-2 border-white" aria-hidden="true" />
            <div>
              <p className="text-gray-300 text-[10px] font-bold uppercase tracking-wide">Selected</p>
              <p className="text-gray-500 text-[10px] leading-tight">
                Solid white ring marks the zone open in the detail panel.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-2 opacity-50">
            <span
              className="w-3 h-3 flex-shrink-0 mt-0.5 border-2 border-dotted border-gray-500"
              aria-hidden="true"
            />
            <div>
              <p className="text-gray-400 text-[10px] font-bold uppercase tracking-wide">
                Simulation — not implemented
              </p>
              <p className="text-gray-600 text-[10px] leading-tight">
                No what-if or forecast overlay exists. Nothing on this map is projected.
              </p>
            </div>
          </div>

          <p className="text-[10px] text-gray-600 leading-tight border-t border-gov-700 pt-1.5">
            CIVICHEAT decision-support thresholds. Not official medical standards.
          </p>
        </div>
      )}
    </div>
  );
}
