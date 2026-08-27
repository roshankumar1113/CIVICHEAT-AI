/**
 * CIVICHEAT hero metrics strip + primary risk indicator. §4 / §5
 *
 * Every number is read from the analysis response. Nothing here is hardcoded —
 * when the backend does not supply a value the tile shows an em dash rather
 * than inventing one.
 */
import { AlertTriangle, Layers, MapPin, Thermometer, TrendingUp } from 'lucide-react';
import type { PriorityAnalysisResult } from '../types';
import { RISK_BADGE_CLASS, riskScoreGradient } from '../utils/risk';
import { riskSummary, temperatureSummary } from '../utils/analysis';

interface HeroMetricsProps {
  result: PriorityAnalysisResult | null;
  /** Tile count reported alongside the analysis, used for the coverage caption. */
  tileCount?: number;
}

interface Tile {
  label: string;
  value: string;
  suffix?: string;
  icon: typeof Thermometer;
  className?: string;
  title: string;
}

function MetricTile({ tile }: { tile: Tile }) {
  const Icon = tile.icon;
  return (
    <div className="bg-gov-800 border border-gov-600 rounded-lg px-3 py-2" title={tile.title}>
      <div className="flex items-center gap-1.5 mb-0.5">
        <Icon size={11} className="text-gray-500 flex-shrink-0" aria-hidden="true" />
        <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest truncate">
          {tile.label}
        </span>
      </div>
      <p className={`text-lg xl:text-xl font-bold font-mono leading-tight ${tile.className ?? 'text-white'}`}>
        {tile.value}
        {tile.suffix && (
          <span className="text-xs text-gray-600 font-normal ml-0.5">{tile.suffix}</span>
        )}
      </p>
    </div>
  );
}

export function HeroMetrics({ result, tileCount }: HeroMetricsProps) {
  const temp = temperatureSummary(result);
  const risk = riskSummary(result);
  const score = result?.highest_risk_score ?? null;
  const level = result?.highest_risk_level ?? null;

  const tiles: Tile[] = [
    {
      label: 'Current Heat Risk',
      value: score === null ? '—' : String(score),
      suffix: score === null ? undefined : '/100',
      icon: TrendingUp,
      className: score === null ? 'text-gray-600' : riskScoreGradient(score),
      title: 'Highest CIVICHEAT Decision-Support Score across all priority zones.',
    },
    {
      label: 'Mean Temperature',
      value: temp ? `${temp.mean_c.toFixed(2)}°C` : '—',
      icon: Thermometer,
      title: 'Mean of average_temperature across every analysed FortyGuard tile.',
    },
    {
      label: 'Max Temperature',
      value: temp ? `${temp.max_c.toFixed(2)}°C` : '—',
      icon: Thermometer,
      className: temp ? 'text-orange-300' : 'text-gray-600',
      title: 'Highest tile temperature observed in this analysis.',
    },
    {
      label: 'Priority Zones',
      value: result ? String(result.priority_zones.length) : '—',
      icon: MapPin,
      title: 'Geographic clusters of HIGH/EXTREME tiles ranked for intervention.',
    },
    {
      label: 'Features Analyzed',
      value: risk ? risk.total_features.toLocaleString() : '—',
      icon: Layers,
      title: 'Total FortyGuard tile features scored by the CIVICHEAT risk engine.',
    },
  ];

  return (
    <section aria-label="Heat response key metrics" className="space-y-2">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
        {tiles.map((tile) => (
          <MetricTile key={tile.label} tile={tile} />
        ))}
      </div>

      {/* Primary risk indicator — large, unmissable, explicitly labelled. §5 */}
      <div className="bg-gov-800 border border-gov-600 rounded-lg px-4 py-3 flex items-center gap-4">
        <div className="flex items-baseline gap-2 flex-shrink-0">
          <span
            className={`text-4xl xl:text-5xl font-bold font-mono leading-none ${
              score === null ? 'text-gray-700' : riskScoreGradient(score)
            }`}
          >
            {score === null ? '—' : score}
          </span>
          <span className="text-sm text-gray-600 font-mono">/100</span>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">
              CIVICHEAT Heat Risk
            </span>
            {level && <span className={RISK_BADGE_CLASS[level]}>{level}</span>}
            {!level && (
              <span className="text-xs text-gray-600 uppercase tracking-wide">Not assessed</span>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            Application-defined decision-support score.
          </p>
          <p className="text-xs text-gray-600 mt-0.5 leading-tight">
            Not a medical or regulatory heat index. Derived from FortyGuard tile temperatures
            only — heat persistence and exceedance data were not available.
          </p>
        </div>

        {result && risk && (
          <div className="hidden xl:block flex-shrink-0 text-right border-l border-gov-700 pl-4">
            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">
              Tile Classification
            </p>
            <div className="space-y-0.5 font-mono text-xs">
              {(['EXTREME', 'HIGH', 'MODERATE', 'LOW'] as const).map((lv) => (
                <div key={lv} className="flex items-center justify-end gap-2">
                  <span className="text-gray-500">{lv}</span>
                  <span className="text-gray-300 w-10 text-right">
                    {risk.feature_counts[lv].toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
            {typeof tileCount === 'number' && tileCount > 0 && (
              <p className="text-[10px] text-gray-600 mt-1 flex items-center justify-end gap-1">
                <AlertTriangle size={9} aria-hidden="true" />
                {tileCount.toLocaleString()} tiles retrieved
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
