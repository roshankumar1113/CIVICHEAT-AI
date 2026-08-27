/**
 * CIVICHEAT Heat Map. §6
 *
 * Three distinct visual layers, each labelled in the legend:
 *   1. TEMPERATURE  filled FortyGuard tiles, coloured by risk threshold
 *   2. PRIORITY     dashed outlines + rank labels for ranked intervention zones
 *   3. SELECTION    solid highlight on the zone currently open in the detail panel
 *
 * A fourth "simulation" layer is intentionally absent — the what-if simulator is
 * not implemented, and the legend says so rather than implying it exists.
 *
 * Tile colour uses fixed risk thresholds, not a stretch of the observed range,
 * so a colour always means the same absolute risk band. When every tile lands in
 * one band the legend reports that explicitly instead of faking variation.
 */
import { useEffect, useRef, useCallback } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { AlertTriangle, Loader2, MapPinned } from 'lucide-react';
import type { PriorityAnalysisResult, PriorityZone, TileFeatureCollection } from '../types';
import { RISK_COLORS } from '../utils/risk';

interface HeatMapProps {
  analysisResult: PriorityAnalysisResult | null;
  tileGeojson?: TileFeatureCollection | null;
  selectedZoneId?: string | null;
  loading?: boolean;
  error?: string | null;
  onZoneClick?: (zone: PriorityZone) => void;
  className?: string;
}

// Phoenix, AZ default center
const DEFAULT_CENTER: [number, number] = [-112.074, 33.4484];
const DEFAULT_ZOOM = 13;

/** Server-side analysis pipeline, shown in the loading overlay. §16 */
const ANALYZE_STAGES = [
  'Retrieving heat intelligence',
  'Calculating heat risk',
  'Finding priority zones',
  'Preparing CIVICHEAT analysis',
] as const;

const LAYER_IDS = [
  'ch-tiles-fill',
  'ch-tiles-outline',
  'ch-zones-fill',
  'ch-zones-outline',
  'ch-zones-selected',
  'ch-zones-labels',
] as const;
const SOURCE_IDS = ['ch-tiles', 'ch-zones'] as const;

/** Match expression mapping a feature's risk_level property to its colour. */
const RISK_LEVEL_COLOR: maplibregl.ExpressionSpecification = [
  'match',
  ['get', 'risk_level'],
  'EXTREME', RISK_COLORS.EXTREME,
  'HIGH', RISK_COLORS.HIGH,
  'MODERATE', RISK_COLORS.MODERATE,
  RISK_COLORS.LOW,
];

export function HeatMap({
  analysisResult,
  tileGeojson,
  selectedZoneId,
  loading = false,
  error = null,
  onZoneClick,
  className = '',
}: HeatMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const styleReady = useRef(false);

  // Click handlers are registered once. They read the latest zones through these
  // refs, so re-analysing never stacks duplicate listeners on the same layer.
  const zonesRef = useRef<PriorityZone[]>([]);
  const onZoneClickRef = useRef<HeatMapProps['onZoneClick']>(onZoneClick);
  zonesRef.current = analysisResult?.priority_zones ?? [];
  onZoneClickRef.current = onZoneClick;

  // Initialize map once
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const m = new maplibregl.Map({
      container: mapContainer.current,
      // Stable free OSM raster style — no API key required
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          },
        },
        layers: [{ id: 'osm-tiles', type: 'raster', source: 'osm' }],
      },
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      attributionControl: false,
    });
    map.current = m;

    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    m.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');

    const handleZoneClick = (
      e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] },
    ) => {
      const zoneId = e.features?.[0]?.properties?.['zone_id'];
      if (typeof zoneId !== 'string') return;
      const zone = zonesRef.current.find((z) => z.zone_id === zoneId);
      if (zone) onZoneClickRef.current?.(zone);
    };
    const enter = () => { m.getCanvas().style.cursor = 'pointer'; };
    const leave = () => { m.getCanvas().style.cursor = ''; };

    m.on('click', 'ch-zones-fill', handleZoneClick);
    m.on('mouseenter', 'ch-zones-fill', enter);
    m.on('mouseleave', 'ch-zones-fill', leave);

    return () => {
      styleReady.current = false;
      m.remove();
      map.current = null;
    };
  }, []);

  // Update layers when analysis data changes
  const updateLayers = useCallback(() => {
    const m = map.current;
    if (!m || !m.isStyleLoaded()) return;

    LAYER_IDS.forEach((id) => {
      if (m.getLayer(id)) m.removeLayer(id);
    });
    SOURCE_IDS.forEach((id) => {
      if (m.getSource(id)) m.removeSource(id);
    });

    if (!analysisResult) return;

    // ── Layer 1: temperature tiles ────────────────────────────────────────────
    if (tileGeojson?.features?.length) {
      m.addSource('ch-tiles', {
        type: 'geojson',
        data: tileGeojson as unknown as GeoJSON.FeatureCollection,
      });
      m.addLayer({
        id: 'ch-tiles-fill',
        type: 'fill',
        source: 'ch-tiles',
        paint: {
          // Fixed thresholds — matches the legend's absolute risk bands.
          'fill-color': [
            'step',
            ['coalesce', ['to-number', ['get', 'average_temperature']], -999],
            '#334155',              // no usable temperature on this tile
            30, RISK_COLORS.LOW,
            35, RISK_COLORS.MODERATE,
            40, RISK_COLORS.HIGH,
            45, RISK_COLORS.EXTREME,
          ],
          'fill-opacity': 0.5,
        },
      });
      m.addLayer({
        id: 'ch-tiles-outline',
        type: 'line',
        source: 'ch-tiles',
        paint: { 'line-color': '#0f172a', 'line-width': 0.3, 'line-opacity': 0.5 },
      });
    }

    // ── Layers 2 & 3: priority zones and the current selection ────────────────
    if (analysisResult.priority_zones.length > 0) {
      const zoneFeatures: GeoJSON.Feature[] = analysisResult.priority_zones.map((z) => ({
        type: 'Feature',
        properties: {
          zone_id: z.zone_id,
          risk_level: z.risk_level,
          risk_score: z.risk_score,
          priority_rank: z.priority_rank,
          label: `#${z.priority_rank} · ${z.zone_id}`,
        },
        geometry: {
          type: 'Polygon',
          coordinates: [[
            [z.bbox[0], z.bbox[1]],
            [z.bbox[2], z.bbox[1]],
            [z.bbox[2], z.bbox[3]],
            [z.bbox[0], z.bbox[3]],
            [z.bbox[0], z.bbox[1]],
          ]],
        },
      }));

      m.addSource('ch-zones', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: zoneFeatures },
      });

      m.addLayer({
        id: 'ch-zones-fill',
        type: 'fill',
        source: 'ch-zones',
        paint: { 'fill-color': RISK_LEVEL_COLOR, 'fill-opacity': 0.1 },
      });

      m.addLayer({
        id: 'ch-zones-outline',
        type: 'line',
        source: 'ch-zones',
        paint: {
          'line-color': RISK_LEVEL_COLOR,
          'line-width': 2.5,
          'line-dasharray': [3, 2],
        },
      });

      // Selection highlight: solid white ring, only on the open zone.
      m.addLayer({
        id: 'ch-zones-selected',
        type: 'line',
        source: 'ch-zones',
        filter: ['==', ['get', 'zone_id'], selectedZoneId ?? '__none__'],
        paint: { 'line-color': '#ffffff', 'line-width': 3.5, 'line-opacity': 0.95 },
      });

      m.addLayer({
        id: 'ch-zones-labels',
        type: 'symbol',
        source: 'ch-zones',
        layout: {
          'text-field': ['get', 'label'],
          'text-size': 12,
          'text-anchor': 'center',
          'text-allow-overlap': false,
        },
        paint: {
          'text-color': '#ffffff',
          'text-halo-color': '#000000',
          'text-halo-width': 1.5,
        },
      });

      // Fly to the data bbox
      const allBbox = analysisResult.priority_zones.reduce(
        (acc, z) => [
          Math.min(acc[0], z.bbox[0]),
          Math.min(acc[1], z.bbox[1]),
          Math.max(acc[2], z.bbox[2]),
          Math.max(acc[3], z.bbox[3]),
        ],
        [Infinity, Infinity, -Infinity, -Infinity],
      );
      if (allBbox[0] !== Infinity && allBbox[0] !== allBbox[2]) {
        m.fitBounds([[allBbox[0], allBbox[1]], [allBbox[2], allBbox[3]]], {
          padding: 60,
          maxZoom: 15,
          duration: 900,
        });
      }
    }
  }, [analysisResult, tileGeojson, selectedZoneId]);

  // Re-run updateLayers when data or style loads
  useEffect(() => {
    const m = map.current;
    if (!m) return;
    if (m.isStyleLoaded()) {
      styleReady.current = true;
      updateLayers();
      return;
    }
    const onLoad = () => {
      styleReady.current = true;
      updateLayers();
    };
    m.once('load', onLoad);
  }, [updateLayers]);

  // Selection changes only need a filter swap, not a full layer rebuild.
  useEffect(() => {
    const m = map.current;
    if (!m || !m.getLayer('ch-zones-selected')) return;
    m.setFilter('ch-zones-selected', ['==', ['get', 'zone_id'], selectedZoneId ?? '__none__']);
  }, [selectedZoneId]);

  const hasZones = (analysisResult?.priority_zones.length ?? 0) > 0;

  return (
    <div className={`relative w-full h-full ${className}`}>
      <div ref={mapContainer} className="w-full h-full" aria-label="Heat intelligence map" />

      <div className="absolute top-3 left-3 pointer-events-none">
        <span className="text-xs font-mono text-white/80 bg-black/60 px-2 py-1 rounded tracking-wider">
          HEAT INTELLIGENCE MAP
        </span>
      </div>

      {/* Error — plain language, no stack trace. §15 */}
      {error && !loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gov-900/85 z-20 p-6">
          <div className="max-w-sm text-center bg-gov-800 border border-red-800 rounded-lg p-5">
            <AlertTriangle size={22} className="text-red-400 mx-auto mb-2" aria-hidden="true" />
            <p className="text-sm font-bold text-red-300 uppercase tracking-wide mb-1">
              Map data unavailable
            </p>
            <p className="text-xs text-gray-400 leading-relaxed">{error}</p>
          </div>
        </div>
      )}

      {/* Analysis ran but produced no priority zones — a real, valid result. */}
      {!loading && !error && analysisResult && !hasZones && (
        <div className="absolute inset-x-0 bottom-20 flex justify-center pointer-events-none px-4">
          <div className="bg-gov-800/95 border border-gov-600 rounded-lg px-4 py-2.5 text-center">
            <p className="text-xs font-bold text-gray-300 uppercase tracking-wide">
              No priority zones detected
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              No tile reached the HIGH threshold in this analysis.
            </p>
          </div>
        </div>
      )}

      {/* Nothing analysed yet */}
      {!loading && !error && !analysisResult && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center bg-gov-900/85 rounded-lg p-6 border border-gov-600">
            <MapPinned size={22} className="text-gray-500 mx-auto mb-2" aria-hidden="true" />
            <p className="text-sm text-gray-300 font-bold uppercase tracking-wide">
              No city analysis yet
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Run ANALYZE CITY to load FortyGuard heat intelligence.
            </p>
          </div>
        </div>
      )}

      {loading && (
        <div className="absolute inset-0 bg-gov-900/75 flex items-center justify-center z-20 pointer-events-none p-6">
          <div className="bg-gov-800/95 border border-gov-600 rounded-lg px-5 py-4 w-full max-w-xs">
            <div className="flex items-center gap-2 mb-3">
              <Loader2 size={14} className="text-blue-400 animate-spin" aria-hidden="true" />
              <span className="text-xs font-bold text-blue-200 uppercase tracking-widest">
                Analyzing City
              </span>
            </div>
            <ol className="space-y-2" aria-label="Analysis pipeline">
              {ANALYZE_STAGES.map((stage, i) => (
                <li key={stage} className="flex items-center gap-2.5 text-xs text-gray-300">
                  <span className="font-mono text-gray-600 w-5 flex-shrink-0">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <Loader2 size={11} className="text-blue-500 animate-spin flex-shrink-0" aria-hidden="true" />
                  <span>{stage}</span>
                </li>
              ))}
            </ol>
            <p className="text-[10px] text-gray-600 mt-3 leading-snug border-t border-gov-700 pt-2">
              Stages run server-side in one request; each is marked done only when the
              backend actually completes it.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
