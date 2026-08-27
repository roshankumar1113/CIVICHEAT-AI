// ─── Core domain types ───────────────────────────────────────────────────────

export type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'EXTREME';
export type DataMode = 'DEMO' | 'LIVE';

// ─── Backend API types ───────────────────────────────────────────────────────

/**
 * Observed state of an upstream integration, as reported by
 * GET /api/system/status. `configured` means credentials exist; `state` means
 * what the backend has actually seen happen. The UI must key CONNECTED off
 * `state`, never off `configured`.
 */
export type IntegrationStateName =
  | 'NOT_CONFIGURED'
  | 'UNVERIFIED'
  | 'CONNECTED'
  | 'DEGRADED'
  | 'AUTH_ERROR'
  | 'TIMEOUT'
  | 'UNAVAILABLE';

export interface IntegrationStatus {
  configured: boolean;
  state: IntegrationStateName;
  detail: string | null;
  checked_at: string | null;
  success_count: number;
  failure_count: number;
}

export interface SystemStatus {
  app_name: string;
  version: string;
  environment: string;
  fortyguard_configured: boolean;
  nemotron_configured: boolean;
  demo_mode: boolean;
  tracks: string[];
  /** Model identifier the backend will actually call. Empty when unconfigured. */
  nemotron_model?: string;
  fortyguard?: IntegrationStatus | null;
  nemotron?: IntegrationStatus | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
}

// ─── FortyGuard / Heat Intelligence ──────────────────────────────────────────

/** A FortyGuard temperature tile as delivered in the GeoJSON FeatureCollection. */
export interface TileFeature {
  id?: string;
  type: 'Feature';
  properties: Record<string, unknown>;
  geometry: Record<string, unknown>;
}

export interface TileFeatureCollection {
  type: 'FeatureCollection';
  features: TileFeature[];
}

export interface HeatIntelligence {
  activity_id: string;
  city: string;
  date: string;
  tile_count: number;
  mean_temperature: number;
  min_temperature: number;
  max_temperature: number;
  std_deviation: number;
  percentiles: number[];
  // GeoJSON FeatureCollection of temperature tiles
  geojson: {
    type: 'FeatureCollection';
    features: Array<{
      id: string;
      type: 'Feature';
      properties: Record<string, unknown>;
      geometry: Record<string, unknown>;
    }>;
  };
  data_mode: DataMode;
}

// ─── Risk Engine ─────────────────────────────────────────────────────────────

export interface AnalysisSummary {
  total_features: number;
  mean_temperature_c: number;
  max_temperature_c: number;
  min_temperature_c: number;
  low_risk_features: number;
  moderate_risk_features: number;
  high_risk_features: number;
  extreme_risk_features: number;
  overall_risk_level: RiskLevel;
  overall_risk_score: number;
  persistence_available: boolean;
  exceedance_available: boolean;
  score_disclaimer: string;
}

export interface FeatureRiskResult {
  feature_id: string;
  temperature_c: number;
  risk_level: RiskLevel;
  risk_score: number;
  reasons: string[];
  temperature_component: number;
  persistence_available: boolean;
  exceedance_available: boolean;
  geometry: Record<string, unknown>;
}

// ─── Priority Zones ──────────────────────────────────────────────────────────

export interface PriorityZone {
  zone_id: string;
  priority_rank: number;
  risk_score: number;
  risk_level: RiskLevel;
  feature_count: number;
  temperature_mean_c: number;
  temperature_max_c: number;
  temperature_min_c: number;
  bbox: [number, number, number, number]; // [west, south, east, north]
  centroid: [number, number];             // [lon, lat]
  reasons: string[];
  recommended_actions: string[];
  action_rationale: string;
}

export interface PriorityAnalysisResult {
  city: string;
  date: string;
  activity_id: string;
  data_mode: DataMode;
  priority_zones: PriorityZone[];
  total_high_extreme_features: number;
  highest_risk_level: RiskLevel;
  highest_risk_score: number;
  agent_context: Record<string, unknown>;
  data_limitations: string[];
}

// ─── API response wrappers ────────────────────────────────────────────────────

export interface AnalyzeResponse {
  success: boolean;
  data_mode: DataMode;
  message: string;
  result: PriorityAnalysisResult;
  /**
   * Raw FortyGuard tile FeatureCollection used by the map's temperature layer.
   * Supplied separately from `result.agent_context` so the per-tile feature set
   * is never handed to the Nemotron agent.
   */
  tile_geojson?: TileFeatureCollection | null;
  tile_count?: number;
}

export interface HeatmapResponse {
  success: boolean;
  intelligence: HeatIntelligence;
  data_mode: DataMode;
  message: string;
}

// ─── UI state ────────────────────────────────────────────────────────────────

export interface AppState {
  mode: DataMode;
  systemStatus: SystemStatus | null;
  loading: boolean;
  error: string | null;
}

// ─── Agent / Nemotron ────────────────────────────────────────────────────────

export interface RecommendedAction {
  action: string;
  reason: string;
  urgency: 'LOW' | 'MEDIUM' | 'HIGH';
}

export interface ReassessmentPlan {
  recommended: boolean;
  interval_minutes: number;
}

export interface AgentDecision {
  decision: string;
  priority_zone: string;
  risk_level: RiskLevel;
  risk_score: number;
  evidence: string[];
  recommended_actions: RecommendedAction[];
  limitations: string[];
  reassessment: ReassessmentPlan;
}

export interface AgentResponse {
  agent: {
    provider: string;
    model: string;
    status: string;
  };
  decision: AgentDecision;
  tools_used: string[];
  fallback_mode: boolean;
  fallback_reason?: string;
}

export interface ActionPlanResponse {
  incident_summary: string;
  priority: RiskLevel;
  zone: string;
  actions: RecommendedAction[];
  evidence: string[];
  limitations: string[];
  reassessment: ReassessmentPlan;
  fallback_mode: boolean;
}

export interface PublicAdvisoryResponse {
  title: string;
  body: string;
  disclaimer: string;
  fallback_mode: boolean;
}

// ─── HeatWatch / Reassessment (Phase 4.5) ────────────────────────────────────

export interface AnalysisSnapshot {
  analysis_id: string;
  timestamp: string;
  city: string;
  date: string;
  data_mode: DataMode;
  mean_temperature_c: number;
  max_temperature_c: number;
  min_temperature_c: number;
  overall_risk_level: RiskLevel;
  overall_risk_score: number;
  priority_zone_count: number;
  priority_zones: Array<Record<string, unknown>>;
}

export type ZoneChangeType =
  | 'new'
  | 'removed'
  | 'rank_shifted'
  | 'score_changed'
  | 'unchanged';

export interface ZoneChange {
  zone_id: string;
  previous_rank: number | null;
  current_rank: number | null;
  previous_score: number | null;
  current_score: number | null;
  change_type: ZoneChangeType;
}

export interface ChangeThresholds {
  risk_score_delta: number;
  mean_temperature_delta_c: number;
  zone_count_change: boolean;
  zone_rank_shift: number;
  disclaimer: string;
}

export interface ComparisonResult {
  previous_snapshot_id: string;
  current_snapshot_id: string;
  mean_temperature_change_c: number;
  max_temperature_change_c: number;
  risk_score_change: number;
  previous_risk_score: number;
  current_risk_score: number;
  previous_risk_level: RiskLevel;
  current_risk_level: RiskLevel;
  previous_zone_count: number;
  current_zone_count: number;
  priority_zone_change: number;
  changed_zones: ZoneChange[];
  meaningful_change: boolean;
  change_reasons: string[];
  thresholds_used: ChangeThresholds;
  disclaimer: string;
}

export interface ReassessmentStatusInfo {
  status: 'SIGNIFICANT_CHANGE' | 'NO_SIGNIFICANT_CHANGE';
  message: string;
}

export interface ReassessmentResponse {
  success: boolean;
  data_mode: DataMode;
  status: ReassessmentStatusInfo;
  comparison: ComparisonResult;
  previous_snapshot: AnalysisSnapshot | null;
  current_snapshot: AnalysisSnapshot;
  // Present only when meaningful change was detected. Shape matches AgentDecision.
  nemotron_decision: AgentDecision | null;
  nemotron_fallback: boolean;
  tools_used: string[];
}

// ─── Resource allocation (Phase 7 placeholder) ───────────────────────────────

export interface ResourceAllocation {
  resource_type: string;
  quantity: number;
  zone_id: string;
  priority: number;
  estimated_impact: string;
}

export interface ResourceConfig {
  budget: number;
  cooling_centers: number;
  mobile_units: number;
  shade_structures: number;
  worker_capacity: number;
}
