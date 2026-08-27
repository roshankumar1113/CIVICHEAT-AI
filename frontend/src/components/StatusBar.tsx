/**
 * CIVICHEAT Command Center header.
 *
 * Reports four things, all sourced from GET /api/system/status or the last
 * completed analysis — never from assumptions:
 *   SYSTEM     backend reachability
 *   DATA       LIVE (FortyGuard) vs DEMO (deterministic sample)
 *   FORTYGUARD CONNECTED / DISCONNECTED — connected only after a real success
 *   NEMOTRON   LIVE / FALLBACK / DISCONNECTED
 */
import type { DataMode, SystemStatus } from '../types';
import {
  DATA_MODE_COPY,
  TONE_CHIP,
  TONE_DOT,
  TONE_TEXT,
  fortyguardChip,
  nemotronChip,
} from '../utils/status';
import type { StatusChip, Tone } from '../utils/status';

interface StatusBarProps {
  status: SystemStatus | null;
  statusLoading: boolean;
  statusError: string | null;
  dataMode?: DataMode | null;
  city?: string;
  date?: string;
}

function Indicator({ label, chip }: { label: string; chip: StatusChip }) {
  return (
    <span
      className="flex items-center gap-1.5 whitespace-nowrap"
      title={`${label}: ${chip.value} — ${chip.detail}`}
    >
      <span className={`inline-block w-2 h-2 rounded-full ${TONE_DOT[chip.tone]}`} aria-hidden="true" />
      <span className="text-gray-500 tracking-wider">{label}</span>
      <span className={`font-bold tracking-wider ${TONE_TEXT[chip.tone]}`}>{chip.value}</span>
    </span>
  );
}

export function StatusBar({
  status,
  statusLoading,
  statusError,
  dataMode,
  city,
  date,
}: StatusBarProps) {
  const backendChip: StatusChip = statusError
    ? { value: 'OFFLINE', tone: 'bad', detail: statusError }
    : statusLoading
      ? { value: 'CONNECTING', tone: 'idle', detail: 'Contacting the CIVICHEAT backend…' }
      : status
        ? { value: 'OPERATIONAL', tone: 'ok', detail: `${status.app_name} v${status.version}` }
        : { value: 'UNKNOWN', tone: 'idle', detail: 'No response from the backend yet.' };

  const fg = fortyguardChip(status?.fortyguard);
  const nem = nemotronChip(status?.nemotron);

  // DATA reflects the mode of the analysis actually on screen. Before any
  // analysis runs there is no data mode to report.
  const dataTone: Tone = dataMode === 'LIVE' ? 'ok' : dataMode === 'DEMO' ? 'warn' : 'idle';
  const dataChip: StatusChip = dataMode
    ? { value: dataMode, tone: dataTone, detail: DATA_MODE_COPY[dataMode] }
    : { value: 'AWAITING ANALYSIS', tone: 'idle', detail: 'No analysis has been run yet.' };

  return (
    <header
      className="bg-gov-800 border-b border-gov-600 flex-shrink-0"
      role="banner"
      aria-label="CIVICHEAT system status"
    >
      <div className="px-3 xl:px-4 py-2 flex items-center justify-between gap-3 text-xs font-mono">
        {/* Identity */}
        <div className="flex items-center gap-2 xl:gap-3 min-w-0">
          <span className="text-blue-400 font-bold tracking-widest uppercase text-sm whitespace-nowrap">
            CIVICHEAT AI
          </span>
          <span className="text-gray-600 hidden sm:inline">|</span>
          <span className="text-gray-400 uppercase tracking-wider hidden sm:inline whitespace-nowrap">
            Heat Response Command Center
          </span>
          {city && (
            <>
              <span className="text-gray-600 hidden lg:inline">|</span>
              <span className="text-gray-300 truncate hidden lg:inline">{city}</span>
              {date && <span className="text-gray-500 hidden xl:inline">{date}</span>}
            </>
          )}
        </div>

        {/* Live indicators */}
        <div className="flex items-center gap-3 xl:gap-5 flex-shrink-0">
          <Indicator label="SYSTEM" chip={backendChip} />
          <Indicator label="DATA" chip={dataChip} />
          <span className="hidden lg:flex items-center gap-3 xl:gap-5">
            <Indicator label="FORTYGUARD" chip={fg} />
            <Indicator label="NEMOTRON" chip={nem} />
          </span>

          {dataMode === 'DEMO' && (
            <span
              className={`px-2 py-0.5 rounded border text-xs font-bold uppercase tracking-wider ${TONE_CHIP.warn}`}
              title="Deterministic data for offline demonstration."
            >
              DEMO MODE
            </span>
          )}
        </div>
      </div>

      {/* Mode banner — LIVE vs DEMO must be unmistakable, never ambiguous. §3 */}
      {dataMode && (
        <div
          className={`px-3 xl:px-4 py-1 text-xs border-t flex items-center gap-2 ${
            dataMode === 'DEMO'
              ? 'bg-yellow-950/60 border-yellow-800/60 text-yellow-200'
              : 'bg-green-950/50 border-green-900/60 text-green-200'
          }`}
          role="status"
        >
          <span className="font-bold tracking-widest uppercase">
            {dataMode === 'DEMO' ? 'DEMO DATA' : 'LIVE DATA'}
          </span>
          <span className="text-gray-600">·</span>
          <span className="opacity-90">{DATA_MODE_COPY[dataMode]}</span>
        </div>
      )}

      {/* Backend unreachable — plain language, never a stack trace. §15 */}
      {statusError && (
        <div
          className="px-3 xl:px-4 py-1 text-xs bg-red-950/70 border-t border-red-900 text-red-200"
          role="alert"
        >
          <span className="font-bold tracking-widest uppercase">BACKEND OFFLINE</span>
          <span className="text-gray-600 mx-2">·</span>
          <span className="opacity-90">
            The CIVICHEAT API is not responding. Start the backend, then reload.
          </span>
        </div>
      )}
    </header>
  );
}
