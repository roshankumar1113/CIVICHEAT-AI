/**
 * CIVICHEAT AI Response Panel — Phase 4 (Nemotron-powered). §9 / §10 / §11
 *
 * Presents the agent as an agent, not a chatbot:
 * - Header names the provider (NVIDIA NEMOTRON) and the actual configured model.
 * - Status is explicit: ● LIVE when the model answered, ● DETERMINISTIC FALLBACK
 *   when the deterministic engine produced the decision. Fallback is never hidden;
 *   when the backend reports why, the reason is shown.
 * - Tool activity is the real tool list the backend returned (§10) and the decision
 *   renders as labelled cards, never raw JSON (§11).
 */
import { useState } from 'react';
import type { ReactNode } from 'react';
import {
  Zap, CheckCircle, Loader2, AlertTriangle,
  Info, ChevronDown, ChevronUp, X, Clock, RefreshCw, Cpu,
} from 'lucide-react';
import type { AgentResponse, PriorityAnalysisResult, PriorityZone } from '../types';
import { RISK_BADGE_CLASS, riskScoreGradient } from '../utils/risk';
import { governmentActions } from '../utils/analysis';
import type { AgentStatus } from '../hooks/useAgent';

// Human-readable tool names for the activity timeline
const TOOL_LABELS: Record<string, string> = {
  get_current_heat_analysis:       'Retrieved heat analysis',
  get_priority_zones:              'Ranked priority zones',
  inspect_zone:                    'Inspected priority zone',
  compare_zones:                   'Compared zones',
  calculate_intervention_priority: 'Evaluated intervention priority',
  generate_government_action_plan: 'Generated action plan',
  generate_public_advisory:        'Generated public advisory',
  request_reassessment:            'Scheduled reassessment',
};

const FALLBACK_MODEL_LABEL = 'CIVICHEAT deterministic engine';

interface AIResponsePanelProps {
  // Phase 3 fallback data (used when agent hasn't run yet)
  result: PriorityAnalysisResult | null;
  targetZone?: PriorityZone | null;
  // Phase 4 agent response
  agentResponse?: AgentResponse | null;
  agentStatus?: AgentStatus;
  /** Configured model the backend will call, from /api/system/status. §9 */
  nemotronModel?: string;
  onClose?: () => void;
  onAsk?: (message: string) => void;
  // Phase 4.5 — trigger a HeatWatch reassessment
  onReassess?: () => void;
}

/** Consistent panel header naming the provider + configured model. §9 */
function PanelHeader({
  model,
  badge,
  onClose,
}: {
  model: string;
  badge?: ReactNode;
  onClose?: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-2">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <Zap size={14} className="text-blue-400 flex-shrink-0" aria-hidden="true" />
          <span className="text-sm font-bold text-blue-300 uppercase tracking-wide">
            CIVICHEAT AI
          </span>
        </div>
        <div className="flex items-center gap-1.5 mt-0.5 text-gray-500">
          <Cpu size={10} aria-hidden="true" />
          <span className="text-[10px] font-mono uppercase tracking-widest">NVIDIA Nemotron</span>
        </div>
        <p className="text-[10px] text-gray-600 font-mono truncate mt-0.5" title={model}>
          {model}
        </p>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {badge}
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
            aria-label="Close AI panel"
          >
            <X size={14} aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
}

function LiveBadge() {
  return (
    <span className="text-xs bg-green-900 text-green-300 border border-green-700 px-2 py-0.5 rounded font-mono whitespace-nowrap">
      ● LIVE
    </span>
  );
}

function FallbackBadge() {
  return (
    <span className="text-xs bg-yellow-900 text-yellow-300 border border-yellow-700 px-2 py-0.5 rounded font-mono whitespace-nowrap">
      ● DETERMINISTIC FALLBACK
    </span>
  );
}

export function AIResponsePanel({
  result,
  targetZone,
  agentResponse,
  agentStatus = 'idle',
  nemotronModel,
  onClose,
  onAsk,
  onReassess,
}: AIResponsePanelProps) {
  const [showLimitations, setShowLimitations] = useState(false);

  const isLoading  = agentStatus === 'loading';
  const isDone     = agentStatus === 'done' && !!agentResponse;
  const isError    = agentStatus === 'error';
  const isFallback = agentResponse?.fallback_mode ?? false;

  const configuredModel = nemotronModel?.trim() || 'Nemotron (model not reported)';

  // ── Render: loading state ──────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="card border border-blue-800 space-y-4">
        <PanelHeader
          model={configuredModel}
          badge={<Loader2 size={14} className="text-blue-400 animate-spin" aria-hidden="true" />}
          onClose={onClose}
        />
        <div className="space-y-2">
          <p className="text-xs text-blue-400 animate-pulse font-mono">
            Nemotron is analyzing…
          </p>
          <div className="space-y-1.5">
            {['Fetching heat intelligence', 'Ranking priority zones', 'Evaluating interventions'].map((step) => (
              <div key={step} className="flex items-center gap-2 text-xs text-gray-500">
                <Loader2 size={10} className="animate-spin text-blue-600" aria-hidden="true" />
                <span>{step}</span>
              </div>
            ))}
          </div>
        </div>
        <p className="text-xs text-gray-600">
          FortyGuard → Risk Engine → Nemotron Agent
        </p>
      </div>
    );
  }

  // ── Render: done (Nemotron response) ──────────────────────────────────────
  if (isDone && agentResponse) {
    const { decision, tools_used, agent, fallback_reason } = agentResponse;
    const urgencyColor = { LOW: 'text-blue-400', MEDIUM: 'text-yellow-400', HIGH: 'text-red-400' };
    const modelShown = isFallback ? FALLBACK_MODEL_LABEL : (agent.model || configuredModel);

    return (
      <div className="card border border-blue-800 space-y-4">
        <PanelHeader
          model={modelShown}
          badge={isFallback ? <FallbackBadge /> : <LiveBadge />}
          onClose={onClose}
        />

        {/* Fallback reason — never hide why the model was not used. §9 */}
        {isFallback && (
          <div className="bg-yellow-950/40 border border-yellow-800/60 rounded px-2.5 py-1.5">
            <p className="text-xs text-yellow-200 leading-snug">
              Nemotron was not used for this decision — the deterministic engine produced it.
              {fallback_reason ? ` ${fallback_reason}` : ''}
            </p>
          </div>
        )}

        {/* Tool Activity Timeline — real tool list from the backend. §10 */}
        {tools_used.length > 0 && (
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-1.5">
              Tool Activity
            </p>
            <div className="space-y-1">
              {tools_used.map((tool, i) => (
                <div key={`${tool}-${i}`} className="flex items-center gap-2 text-xs text-gray-400">
                  <CheckCircle size={11} className="text-green-500 flex-shrink-0" aria-hidden="true" />
                  <span>{TOOL_LABELS[tool] || tool}</span>
                </div>
              ))}
              <div className="flex items-center gap-2 text-xs text-blue-400 font-medium mt-1">
                <CheckCircle size={11} className="text-blue-400 flex-shrink-0" aria-hidden="true" />
                <span>Decision generated</span>
              </div>
            </div>
          </div>
        )}

        {/* Decision summary */}
        <div className="bg-gov-900/50 rounded p-3 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <span className="text-xs text-gray-400 flex-shrink-0">Situation</span>
            <span className="text-xs text-gray-200 text-right">{decision.decision}</span>
          </div>
          {decision.priority_zone && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">Priority Zone</span>
              <span className="text-xs font-bold text-white">{decision.priority_zone}</span>
            </div>
          )}
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">Risk</span>
            <span className={RISK_BADGE_CLASS[decision.risk_level]}>{decision.risk_level}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">Score</span>
            <span className={`text-sm font-bold font-mono ${riskScoreGradient(decision.risk_score)}`}>
              {decision.risk_score}<span className="text-gray-600 text-xs font-normal">/100</span>
            </span>
          </div>
        </div>

        {/* Evidence */}
        {decision.evidence.length > 0 && (
          <div>
            <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-1.5 flex items-center gap-1">
              <Info size={11} aria-hidden="true" /> Evidence
            </p>
            <ul className="space-y-1">
              {decision.evidence.map((e, i) => (
                <li key={i} className="text-xs text-gray-300 flex gap-1.5">
                  <span className="text-gray-600 flex-shrink-0 mt-0.5" aria-hidden="true">•</span>
                  <span>{e}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommended Actions */}
        {decision.recommended_actions.length > 0 && (
          <div>
            <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-1.5 flex items-center gap-1">
              <AlertTriangle size={11} aria-hidden="true" /> Action Plan
            </p>
            <ol className="space-y-2">
              {decision.recommended_actions.map((a, i) => (
                <li key={i} className="text-xs">
                  <div className="flex items-start gap-2">
                    <span className="text-blue-400 font-bold font-mono w-4 flex-shrink-0">{i + 1}.</span>
                    <div className="flex-1">
                      <span className="text-gray-200">{a.action}</span>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={`text-xs font-bold uppercase ${urgencyColor[a.urgency] || 'text-gray-500'}`}>
                          {a.urgency}
                        </span>
                        <span className="text-gray-600 text-xs">{a.reason}</span>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Next reassessment (HeatWatch) */}
        {decision.reassessment.recommended && (
          <div className="bg-gov-900/40 rounded p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-gray-500 uppercase tracking-widest flex items-center gap-1">
                <Clock size={11} aria-hidden="true" /> Next Reassessment
              </span>
              <span className="text-sm text-blue-300 font-mono font-bold">
                {decision.reassessment.interval_minutes} min
              </span>
            </div>
            {onReassess && (
              <button
                onClick={onReassess}
                className="btn-secondary w-full flex items-center justify-center gap-2 text-xs py-1.5"
              >
                <RefreshCw size={12} aria-hidden="true" /> Reassess Now
              </button>
            )}
          </div>
        )}

        {/* Agent metadata */}
        <div className="text-xs text-gray-700 border-t border-gov-700 pt-2 flex justify-between gap-2">
          <span>{isFallback ? 'Deterministic fallback' : agent.provider}</span>
          <span className="font-mono truncate">{modelShown}</span>
        </div>

        {/* Limitations */}
        <div>
          <button
            onClick={() => setShowLimitations(!showLimitations)}
            className="text-xs text-gray-600 hover:text-gray-400 flex items-center gap-1"
            aria-expanded={showLimitations}
          >
            {showLimitations ? <ChevronUp size={11} aria-hidden="true" /> : <ChevronDown size={11} aria-hidden="true" />}
            View limitations
          </button>
          {showLimitations && (
            <ul className="mt-2 space-y-1">
              {decision.limitations.map((l, i) => (
                <li key={i} className="text-xs text-gray-600 flex gap-1.5">
                  <span aria-hidden="true">•</span><span>{l}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    );
  }

  // ── Render: idle / error — show "Ask CIVICHEAT" prompt ────────────────────
  const zone = targetZone || result?.priority_zones[0] || null;
  const deterministicActions = governmentActions(result);

  return (
    <div className="card border border-blue-800 space-y-4">
      <PanelHeader
        model={configuredModel}
        badge={
          <span className="text-xs bg-gov-700 text-gray-400 border border-gov-500 px-2 py-0.5 rounded font-mono whitespace-nowrap">
            STANDBY
          </span>
        }
        onClose={onClose}
      />

      {isError && (
        <div className="bg-red-900/30 border border-red-700 rounded p-2">
          <p className="text-xs text-red-300">⚠ Agent request failed — try again.</p>
        </div>
      )}

      {/* Prompt */}
      {onAsk && (
        <button
          onClick={() => onAsk('What should the government do right now?')}
          className="btn-primary w-full flex items-center justify-center gap-2 text-sm"
          disabled={!result}
        >
          <Zap size={13} aria-hidden="true" />
          Ask CIVICHEAT
        </button>
      )}

      {/* Current context while idle */}
      {zone && (
        <div className="bg-gov-900/50 rounded p-3 space-y-1.5">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Current Context</p>
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">Priority Zone</span>
            <span className="text-white font-bold">{zone.zone_id}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">Risk</span>
            <span className={RISK_BADGE_CLASS[zone.risk_level]}>{zone.risk_level}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">Temperature</span>
            <span className="text-white font-mono">
              {zone.temperature_mean_c.toFixed(1)}°C mean
            </span>
          </div>
        </div>
      )}

      {/* Deterministic actions preview — labelled as rule-engine output, not AI. */}
      {deterministicActions.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1.5 flex items-center gap-1">
            <AlertTriangle size={10} aria-hidden="true" />
            Preliminary Recommendations
          </p>
          <ul className="space-y-1">
            {deterministicActions.slice(0, 3).map((a, i) => (
              <li key={i} className="text-xs text-gray-400 flex gap-1.5">
                <span className="text-gray-600">{i + 1}.</span>
                <span>{a}</span>
              </li>
            ))}
          </ul>
          {onAsk && (
            <p className="text-xs text-gray-600 mt-2">
              Rule-engine output. Click Ask CIVICHEAT for a Nemotron-generated decision.
            </p>
          )}
        </div>
      )}

      {/* Limitations */}
      {result && (
        <div>
          <button
            onClick={() => setShowLimitations(!showLimitations)}
            className="text-xs text-gray-600 hover:text-gray-400 flex items-center gap-1"
            aria-expanded={showLimitations}
          >
            {showLimitations ? <ChevronUp size={11} aria-hidden="true" /> : <ChevronDown size={11} aria-hidden="true" />}
            View data limitations
          </button>
          {showLimitations && (
            <ul className="mt-2 space-y-1">
              {result.data_limitations.map((l, i) => (
                <li key={i} className="text-xs text-gray-600 flex gap-1.5">
                  <span aria-hidden="true">•</span><span>{l}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
