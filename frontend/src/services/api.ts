import axios from 'axios';
import type {
  ActionPlanResponse,
  AgentResponse,
  AnalyzeResponse,
  HeatmapResponse,
  HealthResponse,
  HeatIntelligence,
  PublicAdvisoryResponse,
  ReassessmentResponse,
  SystemStatus,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 90000, // Agent loop can take ~30s with multiple tool calls
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail;
    const message =
      (typeof detail === 'object' ? detail?.message : detail) ||
      error.response?.data?.error ||
      error.message ||
      'An unexpected error occurred';
    return Promise.reject(new Error(message));
  }
);

export interface AnalyzeRequest {
  city?: string;
  date?: string;
  demo_mode?: boolean;
}

export interface AgentAnalyzeRequest {
  message?: string;
  city?: string;
  date?: string;
  demo_mode?: boolean;
}

export interface ActionPlanRequest {
  zone_id: string;
  city?: string;
  date?: string;
  demo_mode?: boolean;
}

export interface ReassessmentRequest {
  city?: string;
  date?: string;
  demo_mode?: boolean;
  invoke_nemotron_on_change?: boolean;
}

export const api = {
  getHealth: (): Promise<HealthResponse> =>
    apiClient.get('/api/health').then((r) => r.data),

  getSystemStatus: (): Promise<SystemStatus> =>
    apiClient.get('/api/system/status').then((r) => r.data),

  /** Full pipeline: FortyGuard → Risk Engine → Priority Zones */
  analyze: (req: AnalyzeRequest = {}): Promise<AnalyzeResponse> =>
    apiClient.post('/api/heatmap/analyze', req).then((r) => r.data),

  /** Raw heatmap only */
  getHeatmap: (req: AnalyzeRequest = {}): Promise<HeatmapResponse> =>
    apiClient.post('/api/heatmap', req).then((r) => r.data),

  /** Risk analysis on a pre-fetched HeatIntelligence object */
  analyzeRisk: (intel: HeatIntelligence) =>
    apiClient.post('/api/risk/analyze', intel).then((r) => r.data),

  // ── Agent endpoints ────────────────────────────────────────────────────────

  /** Ask CIVICHEAT — Nemotron agentic decision support */
  agentAnalyze: (req: AgentAnalyzeRequest = {}): Promise<AgentResponse> =>
    apiClient.post('/api/agent/analyze', req).then((r) => r.data),

  /** Structured government action plan for a specific zone */
  agentActionPlan: (req: ActionPlanRequest): Promise<ActionPlanResponse> =>
    apiClient.post('/api/agent/action-plan', req).then((r) => r.data),

  /** AI-generated public advisory draft */
  agentPublicAdvisory: (req: AnalyzeRequest = {}): Promise<PublicAdvisoryResponse> =>
    apiClient.post('/api/agent/public-advisory', req).then((r) => r.data),

  // ── HeatWatch reassessment (Phase 4.5) ──────────────────────────────────────

  /** Run a continuous heat reassessment: fresh analysis → compare with previous → optional Nemotron */
  runReassessment: (req: ReassessmentRequest = {}): Promise<ReassessmentResponse> =>
    apiClient.post('/api/reassessment/run', req).then((r) => r.data),
};

export default apiClient;
