import { MapPin, Zap, Settings, Activity, RefreshCw, RotateCcw } from 'lucide-react';
import type { PriorityAnalysisResult, SystemStatus } from '../types';
import { HeatStatusPanel } from './HeatStatusPanel';
import { PriorityZoneList } from './PriorityZoneList';
import { SystemStatusPanel } from './SystemStatusPanel';
import { DataLimitations } from './DataLimitations';
import type { PriorityZone } from '../types';

interface SidebarProps {
  result: PriorityAnalysisResult | null;
  loading: boolean;
  selectedZoneId: string | null;
  onSelectZone: (zone: PriorityZone) => void;
  onAnalyzeCity: () => void;
  onAskCivicheat: () => void;
  onOptimizeResources: () => void;
  onGenerateResponsePlan: () => void;
  onReassess: () => void;
  /** §21 — clears the frontend analysis view without touching backend data. */
  onReset: () => void;
  canReset: boolean;
  // §22 — observed backend state, fetched once at the page level.
  status: SystemStatus | null;
  statusLoading: boolean;
  statusError: string | null;
}

export function Sidebar({
  result,
  loading,
  selectedZoneId,
  onSelectZone,
  onAnalyzeCity,
  onAskCivicheat,
  onOptimizeResources,
  onGenerateResponsePlan,
  onReassess,
  onReset,
  canReset,
  status,
  statusLoading,
  statusError,
}: SidebarProps) {
  return (
    <aside className="w-72 bg-gov-800 border-r border-gov-600 flex flex-col overflow-y-auto flex-shrink-0">
      <div className="p-4 space-y-4">
        {/* Heat Status */}
        <HeatStatusPanel result={result} loading={loading} />

        {/* Actions */}
        <div>
          <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">
            Actions
          </h2>
          <div className="flex flex-col gap-2">
            <button
              onClick={onAnalyzeCity}
              disabled={loading}
              className="btn-secondary flex items-center gap-2 text-sm justify-start"
            >
              <MapPin size={13} aria-hidden="true" />
              Analyze City
            </button>
            <button
              onClick={onAskCivicheat}
              disabled={loading || !result}
              className="btn-primary flex items-center gap-2 text-sm justify-start"
            >
              <Zap size={13} aria-hidden="true" />
              Ask CIVICHEAT
            </button>
            <button
              onClick={onOptimizeResources}
              disabled={true}
              title="Available in Phase 7"
              className="btn-secondary flex items-center gap-2 text-sm justify-start opacity-50 cursor-not-allowed"
            >
              <Settings size={13} aria-hidden="true" />
              Optimize Resources
              <span className="text-xs text-gray-600 ml-auto">Phase 7</span>
            </button>
            <button
              onClick={onGenerateResponsePlan}
              disabled={loading || !result}
              className="btn-secondary flex items-center gap-2 text-sm justify-start"
            >
              <Activity size={13} aria-hidden="true" />
              Generate Response Plan
            </button>
            <button
              onClick={onReassess}
              disabled={loading}
              className="btn-secondary flex items-center gap-2 text-sm justify-start"
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} aria-hidden="true" />
              Reassess
            </button>
            <button
              onClick={onReset}
              disabled={loading || !canReset}
              title="Clear the current analysis, selected zone, AI response and reassessment. Backend data is not deleted."
              className="btn-secondary flex items-center gap-2 text-sm justify-start disabled:opacity-40"
            >
              <RotateCcw size={13} aria-hidden="true" />
              Reset Analysis
            </button>
          </div>
        </div>

        {/* Priority Zone list */}
        {result && (
          <PriorityZoneList
            zones={result.priority_zones}
            selectedZoneId={selectedZoneId}
            onSelect={onSelectZone}
          />
        )}

        {/* System status + limitations */}
        <div className="space-y-2">
          <SystemStatusPanel status={status} loading={statusLoading} error={statusError} />
          <DataLimitations />
        </div>

        {/* Footer */}
        <div className="mt-auto pt-2">
          <p className="text-xs text-gray-700 text-center">CIVICHEAT AI v0.1.0</p>
          <p className="text-xs text-gray-700 text-center">FortyGuard + Nemotron</p>
        </div>
      </div>
    </aside>
  );
}
