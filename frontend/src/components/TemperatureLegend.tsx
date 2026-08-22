import { RISK_COLORS } from '../utils/risk';

interface TemperatureLegendProps {
  unit?: 'C' | 'F';
}

const LEGEND_ITEMS = [
  { level: 'LOW',      label: '< 30°C',      color: RISK_COLORS.LOW },
  { level: 'MODERATE', label: '30 – 34.9°C', color: RISK_COLORS.MODERATE },
  { level: 'HIGH',     label: '35 – 39.9°C', color: RISK_COLORS.HIGH },
  { level: 'EXTREME',  label: '≥ 40°C',      color: RISK_COLORS.EXTREME },
] as const;

export function TemperatureLegend({ unit = 'C' }: TemperatureLegendProps) {
  return (
    <div className="bg-gov-800/90 border border-gov-600 rounded-lg p-3 backdrop-blur-sm">
      <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">
        Temperature ({unit})
      </p>
      <div className="space-y-1.5">
        {LEGEND_ITEMS.map((item) => (
          <div key={item.level} className="flex items-center gap-2">
            <span
              className="w-4 h-4 rounded-sm flex-shrink-0"
              style={{ backgroundColor: item.color, opacity: 0.85 }}
            />
            <span className="text-xs text-gray-300 font-mono">{item.label}</span>
            <span className="text-xs text-gray-500 uppercase tracking-wide ml-1">
              {item.level}
            </span>
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-600 mt-2 leading-tight">
        CIVICHEAT Decision-Support thresholds.
        <br />Not official medical standards.
      </p>
    </div>
  );
}
