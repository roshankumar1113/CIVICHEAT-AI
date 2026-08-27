/**
 * SYSTEM STATUS panel. §22
 *
 * A detailed, honest read of the backend's reported state — retrieved from
 * GET /api/system/status and passed down (the fetch is lifted to the page so it
 * happens exactly once). Adds the local Risk Engine / Priority services that the
 * top status bar does not show, plus the configured Nemotron model.
 *
 * Nothing here is upgraded: FortyGuard / Nemotron reflect observed call outcomes,
 * and the local engines report Ready only while the backend is actually reachable.
 */
import { useState } from 'react';
import { ChevronDown, ChevronUp, Server } from 'lucide-react';
import type { SystemStatus } from '../types';
import { TONE_DOT, TONE_TEXT, fortyguardChip, nemotronChip } from '../utils/status';
import type { StatusChip, Tone } from '../utils/status';

interface SystemStatusPanelProps {
  status: SystemStatus | null;
  loading: boolean;
  error: string | null;
}

function Row({ label, chip }: { label: string; chip: StatusChip }) {
  return (
    <div className="flex items-center justify-between gap-2 text-xs" title={chip.detail}>
      <span className="text-gray-400">{label}</span>
      <span className="flex items-center gap-1.5">
        <span className={`inline-block w-1.5 h-1.5 rounded-full ${TONE_DOT[chip.tone]}`} aria-hidden="true" />
        <span className={`font-mono ${TONE_TEXT[chip.tone]}`}>{chip.value}</span>
      </span>
    </div>
  );
}

export function SystemStatusPanel({ status, loading, error }: SystemStatusPanelProps) {
  const [expanded, setExpanded] = useState(false);

  const online = !!status && !error;

  // Local deterministic services are Ready only while the backend answers.
  const localChip: StatusChip = error
    ? { value: 'OFFLINE', tone: 'bad', detail: 'Backend is not reachable.' }
    : loading
      ? { value: 'CHECKING', tone: 'idle', detail: 'Contacting the CIVICHEAT backend…' }
      : online
        ? { value: 'READY', tone: 'ok', detail: 'Local deterministic engine available.' }
        : { value: 'UNKNOWN', tone: 'idle', detail: 'No backend response yet.' };

  const fg = fortyguardChip(status?.fortyguard);
  const nem = nemotronChip(status?.nemotron);

  // Aggregate dot for the collapsed header: worst-of.
  const overall: Tone = error
    ? 'bad'
    : loading
      ? 'idle'
      : [fg.tone, nem.tone].includes('bad')
        ? 'warn'
        : 'ok';

  const model = status?.nemotron_model?.trim();

  return (
    <div className="border border-gov-600 rounded-lg bg-gov-800/60">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2 flex items-center justify-between text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg"
        aria-expanded={expanded}
        aria-controls="system-status-list"
      >
        <span className="flex items-center gap-1.5 text-xs font-bold text-gray-400 uppercase tracking-widest">
          <Server size={12} className="text-gray-500" aria-hidden="true" />
          System Status
        </span>
        <span className="flex items-center gap-2">
          <span className={`inline-block w-2 h-2 rounded-full ${TONE_DOT[overall]}`} aria-hidden="true" />
          {expanded ? (
            <ChevronUp size={13} className="text-gray-500" aria-hidden="true" />
          ) : (
            <ChevronDown size={13} className="text-gray-500" aria-hidden="true" />
          )}
        </span>
      </button>

      {expanded && (
        <div id="system-status-list" className="px-3 pb-3 pt-1 space-y-1.5 border-t border-gov-700">
          <Row label="FortyGuard" chip={fg} />
          <Row label="Risk Engine" chip={localChip} />
          <Row label="Priority" chip={localChip} />
          <Row label="Nemotron" chip={nem} />

          <div className="border-t border-gov-700 pt-1.5 mt-1.5 space-y-1">
            <div className="flex items-center justify-between gap-2 text-xs">
              <span className="text-gray-500">Model</span>
              <span className="font-mono text-gray-300 truncate max-w-[10rem]" title={model || 'Not configured'}>
                {model || '—'}
              </span>
            </div>
            <div className="flex items-center justify-between gap-2 text-xs">
              <span className="text-gray-500">Backend</span>
              <span className="font-mono text-gray-400">
                {status ? `${status.app_name} v${status.version}` : '—'}
              </span>
            </div>
            {status?.environment && (
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="text-gray-500">Environment</span>
                <span className="font-mono text-gray-400 uppercase">{status.environment}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
