import { useState, useCallback } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';
import { StatusBar } from '../components/StatusBar';
import { Sidebar } from '../components/Sidebar';
import { HeatMap } from '../components/HeatMap';
import { HeroMetrics } from '../components/HeroMetrics';
import { TemperatureLegend } from '../components/TemperatureLegend';
import { ZoneDetailPanel } from '../components/ZoneDetailPanel';
import { AIResponsePanel } from '../components/AIResponsePanel';
import { HeatWatchPanel } from '../components/HeatWatchPanel';
import { useAnalysis } from '../hooks/useAnalysis';
import { useAgent } from '../hooks/useAgent';
import { useReassessment } from '../hooks/useReassessment';
import { useSystemStatus } from '../hooks/useSystemStatus';
import type { PriorityZone } from '../types';

const DEFAULT_CITY = 'Phoenix, AZ';
const DEFAULT_DATE = '2025-08-01';

export function Dashboard() {
  const { result, loading, error, run, reset: analysisReset } = useAnalysis();
  const { response: agentResponse, status: agentStatus, ask: agentAsk, reset: agentReset } = useAgent();
  const {
    response: reassessResponse,
    status: reassessStatus,
    error: reassessError,
    run: reassessRun,
    reset: reassessReset,
  } = useReassessment();

  // Observed backend state — fetched once here, shared with the header and the
  // system-status panel so there is a single /api/system/status request. §22/§23
  const { status, loading: statusLoading, error: statusError } = useSystemStatus();

  const [selectedZone, setSelectedZone] = useState<PriorityZone | null>(null);
  const [showAIPanel, setShowAIPanel] = useState(false);
  const [showHeatWatch, setShowHeatWatch] = useState(false);
  const [aiTargetZone, setAiTargetZone] = useState<PriorityZone | null>(null);

  const analysis = result?.result ?? null;

  // Derive demo mode from last result — if no result yet, backend decides
  const demoMode = result?.data_mode === 'DEMO';

  // Next-reassessment cadence surfaced by the last agent decision (default 60)
  const reassessInterval = agentResponse?.decision.reassessment.interval_minutes ?? 60;

  const agentBusy = agentStatus === 'loading';

  const handleAnalyzeCity = useCallback(async () => {
    setSelectedZone(null);
    setShowAIPanel(false);
    setShowHeatWatch(false);
    agentReset();
    reassessReset();
    await run(DEFAULT_CITY, DEFAULT_DATE, false);
  }, [run, agentReset, reassessReset]);

  const handleReassess = useCallback(async () => {
    setSelectedZone(null);
    setShowAIPanel(false);
    setShowHeatWatch(true);
    await reassessRun(DEFAULT_CITY, DEFAULT_DATE, demoMode);
  }, [reassessRun, demoMode]);

  // Open AI panel and immediately trigger agent
  const handleAskCivicheat = useCallback(async (message?: string) => {
    setAiTargetZone(analysis?.priority_zones[0] ?? null);
    setShowHeatWatch(false);
    setShowAIPanel(true);
    await agentAsk(
      message ?? 'What should the government do right now?',
      DEFAULT_CITY,
      DEFAULT_DATE,
      demoMode,
    );
  }, [analysis, agentAsk, demoMode]);

  const handleZoneAskAI = useCallback(async (zone: PriorityZone) => {
    setAiTargetZone(zone);
    setShowHeatWatch(false);
    setShowAIPanel(true);
    await agentAsk(
      `What should the government do about ${zone.zone_id}? It has ${zone.risk_level} risk with a mean temperature of ${zone.temperature_mean_c.toFixed(1)}°C.`,
      DEFAULT_CITY,
      DEFAULT_DATE,
      demoMode,
    );
  }, [agentAsk, demoMode]);

  const handleGenerateResponsePlan = useCallback(async () => {
    setAiTargetZone(null);
    setShowHeatWatch(false);
    setShowAIPanel(true);
    await agentAsk(
      'Generate a complete government heat response plan for the current conditions.',
      DEFAULT_CITY,
      DEFAULT_DATE,
      demoMode,
    );
  }, [agentAsk, demoMode]);

  const handleZoneSelect = useCallback((zone: PriorityZone) => {
    setSelectedZone((prev) => (prev?.zone_id === zone.zone_id ? null : zone));
    setShowAIPanel(false);
    setShowHeatWatch(false);
  }, []);

  const handleCloseAIPanel = useCallback(() => {
    setShowAIPanel(false);
    agentReset();
  }, [agentReset]);

  const handleCloseHeatWatch = useCallback(() => {
    setShowHeatWatch(false);
    reassessReset();
  }, [reassessReset]);

  // §21 — clear the whole frontend view. Backend snapshots are left intact.
  const canReset =
    !!analysis || !!selectedZone || showAIPanel || showHeatWatch || !!agentResponse || !!reassessResponse;

  const handleReset = useCallback(() => {
    setSelectedZone(null);
    setShowAIPanel(false);
    setShowHeatWatch(false);
    setAiTargetZone(null);
    agentReset();
    reassessReset();
    analysisReset();
  }, [agentReset, reassessReset, analysisReset]);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-gov-900">
      {/* Top bar */}
      <StatusBar
        status={status}
        statusLoading={statusLoading}
        statusError={statusError}
        dataMode={result?.data_mode ?? null}
        city={analysis?.city}
        date={analysis?.date}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <Sidebar
          result={analysis}
          loading={loading}
          selectedZoneId={selectedZone?.zone_id ?? null}
          onSelectZone={handleZoneSelect}
          onAnalyzeCity={handleAnalyzeCity}
          onAskCivicheat={() => { void handleAskCivicheat(); }}
          onOptimizeResources={() => { /* Phase 7 */ }}
          onGenerateResponsePlan={() => { void handleGenerateResponsePlan(); }}
          onReassess={handleReassess}
          onReset={handleReset}
          canReset={canReset}
          status={status}
          statusLoading={statusLoading}
          statusError={statusError}
        />

        {/* Main map */}
        <main className="flex-1 flex flex-col relative overflow-hidden">
          <div className="px-4 pt-3 pb-1 flex-shrink-0 flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h1 className="text-sm font-bold text-white tracking-widest uppercase">
                Command Center
              </h1>
              <p className="text-xs text-gray-600">
                {loading
                  ? 'Analyzing temperature intelligence…'
                  : analysis
                  ? `${analysis.total_high_extreme_features ?? 0} high/extreme tiles · ${analysis.priority_zones?.length ?? 0} priority zones`
                  : 'Click Analyze City to load FortyGuard heat intelligence'}
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {error && (
                <div className="bg-red-900/40 border border-red-700 rounded px-3 py-1.5 flex items-center gap-1.5">
                  <AlertTriangle size={12} className="text-red-400" aria-hidden="true" />
                  <p className="text-xs text-red-300">{error}</p>
                </div>
              )}
              {canReset && (
                <button
                  onClick={handleReset}
                  disabled={loading}
                  className="btn-secondary text-xs flex items-center gap-1.5 py-1.5 disabled:opacity-40"
                  aria-label="Reset analysis view"
                  title="Clear the current analysis view. Backend data is not deleted."
                >
                  <RotateCcw size={12} aria-hidden="true" />
                  Reset
                </button>
              )}
            </div>
          </div>

          {/* Hero metrics — only once real values exist. §4 / §5 */}
          {analysis && (
            <div className="px-4 pb-1 flex-shrink-0">
              <HeroMetrics result={analysis} tileCount={result?.tile_count} />
            </div>
          )}

          <div className="flex-1 relative mx-4 mb-4 mt-1 rounded-lg overflow-hidden border border-gov-600">
            <HeatMap
              analysisResult={analysis}
              tileGeojson={result?.tile_geojson ?? null}
              selectedZoneId={selectedZone?.zone_id ?? null}
              loading={loading}
              error={error}
              onZoneClick={handleZoneSelect}
            />

            <div className="absolute bottom-4 left-4 z-10">
              <TemperatureLegend result={analysis} />
            </div>
          </div>
        </main>

        {/* Right panel */}
        {(selectedZone || showAIPanel || showHeatWatch) && (
          <aside className="w-80 bg-gov-800 border-l border-gov-600 overflow-y-auto flex-shrink-0 p-4 space-y-4">
            {selectedZone && !showAIPanel && !showHeatWatch && (
              <ZoneDetailPanel
                zone={selectedZone}
                onClose={() => setSelectedZone(null)}
                onAskAI={(zone) => { void handleZoneAskAI(zone); }}
                askDisabled={agentBusy}
              />
            )}
            {showAIPanel && (
              <AIResponsePanel
                result={analysis}
                targetZone={aiTargetZone}
                agentResponse={agentResponse}
                agentStatus={agentStatus}
                nemotronModel={status?.nemotron_model}
                onClose={handleCloseAIPanel}
                onAsk={(msg) => { void handleAskCivicheat(msg); }}
                onReassess={() => { void handleReassess(); }}
              />
            )}
            {showHeatWatch && (
              <HeatWatchPanel
                response={reassessResponse}
                status={reassessStatus}
                error={reassessError}
                intervalMinutes={reassessInterval}
                onReassess={() => { void handleReassess(); }}
                onClose={handleCloseHeatWatch}
              />
            )}
          </aside>
        )}
      </div>
    </div>
  );
}
