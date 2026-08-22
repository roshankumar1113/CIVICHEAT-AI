/**
 * CIVICHEAT Heat Map
 * Renders FortyGuard GeoJSON tile data + priority zone overlays via MapLibre GL JS.
 */
import { useEffect, useRef, useCallback } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { PriorityAnalysisResult, PriorityZone } from '../types';
import { RISK_COLORS } from '../utils/risk';

interface HeatMapProps {
  analysisResult: PriorityAnalysisResult | null;
  onZoneClick?: (zone: PriorityZone) => void;
  className?: string;
}

// Phoenix, AZ default center
const DEFAULT_CENTER: [number, number] = [-112.074, 33.4484];
const DEFAULT_ZOOM = 13;

export function HeatMap({ analysisResult, onZoneClick, className = '' }: HeatMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);

  // Initialize map once
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      // Stable free OSM raster style — no API key required
      style: {
        version: 8,
        sources: {
          'osm': {
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

    map.current.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.current.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      'bottom-right'
    );

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  // Update layers when analysis data changes
  const updateLayers = useCallback(() => {
    const m = map.current;
    if (!m || !m.isStyleLoaded()) return;

    // Remove existing CIVICHEAT layers/sources
    ['ch-zones-fill', 'ch-zones-outline', 'ch-zones-labels', 'ch-tiles-fill'].forEach((id) => {
      if (m.getLayer(id)) m.removeLayer(id);
    });
    ['ch-tiles', 'ch-zones'].forEach((id) => {
      if (m.getSource(id)) m.removeSource(id);
    });

    if (!analysisResult) return;

    // ── Temperature tile layer (raw FortyGuard GeoJSON) ───────────────────────
    const tilesGeojson = analysisResult.agent_context?.['geojson'] as GeoJSON.FeatureCollection | undefined;

    if (tilesGeojson?.features?.length) {
      m.addSource('ch-tiles', { type: 'geojson', data: tilesGeojson });
      m.addLayer({
        id: 'ch-tiles-fill',
        type: 'fill',
        source: 'ch-tiles',
        paint: {
          'fill-color': [
            'interpolate', ['linear'],
            ['get', 'average_temperature'],
            30, RISK_COLORS.LOW,
            35, RISK_COLORS.MODERATE,
            40, RISK_COLORS.HIGH,
            45, RISK_COLORS.EXTREME,
          ],
          'fill-opacity': 0.55,
        },
      });
    }

    // ── Priority zone layer ───────────────────────────────────────────────────
    if (analysisResult.priority_zones.length > 0) {
      const zoneFeatures: GeoJSON.Feature[] = analysisResult.priority_zones.map((z) => ({
        type: 'Feature',
        properties: {
          zone_id: z.zone_id,
          risk_level: z.risk_level,
          risk_score: z.risk_score,
          priority_rank: z.priority_rank,
          temperature_mean_c: z.temperature_mean_c,
          temperature_max_c: z.temperature_max_c,
          feature_count: z.feature_count,
          action_rationale: z.action_rationale,
          label: `#${z.priority_rank}`,
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
        paint: {
          'fill-color': [
            'match', ['get', 'risk_level'],
            'EXTREME', RISK_COLORS.EXTREME,
            'HIGH',    RISK_COLORS.HIGH,
            'MODERATE', RISK_COLORS.MODERATE,
            RISK_COLORS.LOW,
          ],
          'fill-opacity': 0.12,
        },
      });

      m.addLayer({
        id: 'ch-zones-outline',
        type: 'line',
        source: 'ch-zones',
        paint: {
          'line-color': [
            'match', ['get', 'risk_level'],
            'EXTREME', RISK_COLORS.EXTREME,
            'HIGH',    RISK_COLORS.HIGH,
            'MODERATE', RISK_COLORS.MODERATE,
            RISK_COLORS.LOW,
          ],
          'line-width': 2.5,
          'line-dasharray': [3, 2],
        },
      });

      m.addLayer({
        id: 'ch-zones-labels',
        type: 'symbol',
        source: 'ch-zones',
        layout: {
          'text-field': ['get', 'label'],
          'text-size': 14,
          'text-anchor': 'center',
        },
        paint: {
          'text-color': '#ffffff',
          'text-halo-color': '#000000',
          'text-halo-width': 1.5,
        },
      });

      // Click handler for zones
      m.on('click', 'ch-zones-fill', (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
        if (!e.features?.length) return;
        const props = e.features[0].properties;
        const zone = analysisResult.priority_zones.find(
          (z) => z.zone_id === props.zone_id
        );
        if (zone && onZoneClick) onZoneClick(zone);
      });

      m.on('mouseenter', 'ch-zones-fill', () => {
        m.getCanvas().style.cursor = 'pointer';
      });
      m.on('mouseleave', 'ch-zones-fill', () => {
        m.getCanvas().style.cursor = '';
      });
    }

    // Fly to the data bbox
    if (analysisResult.priority_zones.length > 0) {
      const allBbox = analysisResult.priority_zones.reduce(
        (acc, z) => [
          Math.min(acc[0], z.bbox[0]),
          Math.min(acc[1], z.bbox[1]),
          Math.max(acc[2], z.bbox[2]),
          Math.max(acc[3], z.bbox[3]),
        ],
        [Infinity, Infinity, -Infinity, -Infinity]
      );
      if (allBbox[0] !== Infinity) {
        m.fitBounds(
          [[allBbox[0], allBbox[1]], [allBbox[2], allBbox[3]]],
          { padding: 60, maxZoom: 15, duration: 1000 }
        );
      }
    }
  }, [analysisResult, onZoneClick]);

  // Re-run updateLayers when data or style loads
  useEffect(() => {
    const m = map.current;
    if (!m) return;
    if (m.isStyleLoaded()) {
      updateLayers();
    } else {
      m.once('load', updateLayers);
    }
  }, [updateLayers]);

  return (
    <div className={`relative w-full h-full ${className}`}>
      <div ref={mapContainer} className="w-full h-full" />

      {/* Corner labels */}
      <div className="absolute top-3 left-3 pointer-events-none">
        <span className="text-xs font-mono text-white/70 bg-black/50 px-2 py-1 rounded">
          HEAT INTELLIGENCE MAP
        </span>
      </div>

      {!analysisResult && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center bg-gov-900/80 rounded-lg p-6 border border-gov-600">
            <p className="text-gray-400 text-sm">Click ANALYZE CITY to load heat intelligence</p>
          </div>
        </div>
      )}
    </div>
  );
}
