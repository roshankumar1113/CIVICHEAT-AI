import { useSystemStatus } from '../hooks/useSystemStatus';

interface StatusBarProps {
  dataMode?: 'LIVE' | 'DEMO' | null;
  city?: string;
  date?: string;
}

export function StatusBar({ dataMode, city, date }: StatusBarProps) {
  const { status, loading, error } = useSystemStatus();

  const dot = (active: boolean, pulse = false) => (
    <span
      className={`inline-block w-2 h-2 rounded-full mr-1.5 ${
        active ? 'bg-green-400' : 'bg-red-500'
      } ${pulse && active ? 'animate-pulse' : ''}`}
    />
  );

  return (
    <header className="bg-gov-800 border-b border-gov-600 px-4 py-2 flex items-center justify-between text-xs font-mono flex-shrink-0">
      <div className="flex items-center gap-4">
        <span className="text-blue-400 font-bold tracking-widest uppercase text-sm">
          CIVICHEAT AI
        </span>
        <span className="text-gray-600">|</span>
        <span className="text-gray-500">Track 4 — Gov &amp; Environment</span>
        <span className="text-gray-500">Track 6 — Agentic AI</span>
        {city && (
          <>
            <span className="text-gray-600">|</span>
            <span className="text-gray-400">{city}</span>
            {date && <span className="text-gray-500">{date}</span>}
          </>
        )}
      </div>

      <div className="flex items-center gap-5">
        {loading && <span className="text-gray-500 animate-pulse">Connecting…</span>}
        {error   && <span className="text-red-400">⚠ Backend unreachable</span>}

        {status && (
          <>
            <span>{dot(true)}<span className="text-gray-300">Backend</span></span>
            <span>{dot(status.fortyguard_configured, true)}<span className="text-gray-300">FortyGuard</span></span>
            <span>{dot(status.nemotron_configured)}<span className="text-gray-300">Nemotron</span></span>
          </>
        )}

        {dataMode && (
          <span
            className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
              dataMode === 'DEMO'
                ? 'bg-yellow-900 text-yellow-300 border border-yellow-700'
                : 'bg-green-900 text-green-300 border border-green-700'
            }`}
          >
            {dataMode === 'DEMO' ? '⚠ DEMO DATA' : '● LIVE FORTYGUARD'}
          </span>
        )}
      </div>
    </header>
  );
}
