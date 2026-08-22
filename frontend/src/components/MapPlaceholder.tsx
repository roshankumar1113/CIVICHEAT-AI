export function MapPlaceholder() {
  return (
    <div className="flex-1 bg-gov-900 relative flex items-center justify-center border border-gov-700 rounded-lg m-4">
      <div className="text-center">
        <div className="text-6xl mb-4">🗺️</div>
        <p className="text-gray-400 text-sm font-mono">
          Heat map visualization
        </p>
        <p className="text-gray-600 text-xs mt-1">
          MapLibre GL JS — Phase 3
        </p>
        <p className="text-xs text-yellow-600 mt-3 font-mono uppercase tracking-wider">
          Demo Mode — No live data yet
        </p>
      </div>

      {/* Corner labels */}
      <span className="absolute top-3 left-3 text-xs font-mono text-gray-600">
        HEAT INTELLIGENCE MAP
      </span>
      <span className="absolute top-3 right-3 text-xs font-mono bg-yellow-900 text-yellow-400 px-2 py-0.5 rounded border border-yellow-700">
        DEMO MODE
      </span>
      <span className="absolute bottom-3 left-3 text-xs text-gray-700 font-mono">
        FortyGuard — Phase 2
      </span>
    </div>
  );
}
