/**
 * CIVICHEAT AI Response Panel — Phase 4 (Nemotron-powered)
 *
 * Shows:
 * - Agent status (LIVE / FALLBACK / loading)
 * - Tool activity timeline (visible for Track 6 judges)
 * - Structured decision with evidence and recommended actions
 * - Limitations section
 *
 * Never displays raw chain-of-thought.
 * Clearly labels FALLBACK MODE when Nemotron is unavailable.
 */
import { useState } from 'react';
import {
  Zap, CheckCircle, Loader2, AlertTriangle,
  Info, ChevronDown, ChevronUp, X, Clock, RefreshCw
} from 'lucide-react';
import type { AgentResponse, PriorityAnalysisResult, PriorityZone } from '../types';
import { RISK_BADGE_CLASS, riskScoreGradient } from '../utils/risk';
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

interface AIResponsePanelProps {
  // Phase 3 fallback data (used when agent hasn't run yet)
  result: PriorityAnalysisResult | null;
  targetZone?: PriorityZone | null;
  // Phase 4 agent response
  agentResponse?: AgentResponse | null;
  agentStatus?: AgentStatus;
  onClose?: () => void;
  onAsk?: (message: string) => void;
  // Phase 4.5 — trigger a HeatWatch reassessment
  onReassess?: () => void;
}

export function AIResponsePanel({
  result,
  targetZone,
  agentResponse,
  agentStatus = 'idle',
  onClose,
  onAsk,
  onReassess,
}: AIResponsePanelProps) {
  const [showLimitations, setShowLimitations] = useState(false);

  const isLoading  = agentStatus === 'loading';
  const isDone     = agentStatus === 'done' && !!agentResponse;
  const isError    = agentStatus === 'error';
  const isFallback = agentResponse?.fallback_mode ?? false;

  // ── Render: loading state ──────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="card border border-blue-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Loader2 size={14} className="text-blue-400 animate-spin" />
            <span className="text-sm font-bold text-blue-300 uppercase tracking-wide">
              CIVICHEAT AI
            </span>
          </div>
          {onClose && (
            <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-xs">
              <X size={14} />
            </button>
          )}
        </div>
        <div className="space-y-2">
          <p className="text-xs text-blue-400 animate-pulse font-mono">
            Nemotron is analyzing…
          </p>
          <div className="space-y-1.5">
            {['Fetching heat intelligence', 'Ranking priority zones', 'Evaluating interventions'].map((step, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-gray-500">
                <Loader2 size={10} className="animate-spin text-blue-600" />
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
    const { decision, tools_used, agent } = agentResponse;
    const urgencyColor = { LOW: 'text-blue-400', MEDIUM: 'text-yellow-400', HIGH: 'text-red-400' };

    return (
      <div className="card border border-blue-800 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap size={14} className="text-blue-400" />
            <span className="text-sm font-bold text-blue-300 uppercase tracking-wide">
              AI Decision
            </span>
          </div>
          <div className="flex items-center gap-2">
            {isFallback ? (
              <span className="text-xs bg-yellow-900 text-yellow-300 border border-yellow-700 px-2 py-0.5 rounded font-mono">
                FALLBACK MODE
              </span>
            ) : (
              <span className="text-xs bg-green-900 text-green-300 border border-green-700 px-2 py-0.5 rounded font-mono">
                ● NEMOTRON LIVE
              </span>
            )}
            {onClose && (
              <button onClick={onClose} className="text-gray-500 hover:text-gray-300">
                <X size={14} />
              </button>
            )}
          </div>
        </div>

        {/* Tool Activity Timeline */}
        {tools_used.length > 0 && (
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-1.5">
              Tool Activity
            </p>
            <div className="space-y-1">
              {tools_used.map((tool, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-gray-400">
                  <CheckCircle size={11} className="text-green-500 flex-shrink-0" />
                  <span>{TOOL_LABELS[tool] || tool}</span>
                </div>
              ))}
              <div className="flex items-center gap-2 text-xs text-blue-400 font-medium mt-1">
                <CheckCircle size={11} className="text-blue-400 flex-shrink-0" />
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
              <Info size={11} /> Evidence
            </p>
            <ul className="space-y-1">
              {decision.evidence.map((e, i) => (
                <li key={i} className="text-xs text-gray-300 flex gap-1.5">
                  <span className="text-gray-600 flex-shrink-0 mt-0.5">•</span>
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
              <AlertTriangle size={11} /> Action Plan
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
                <Clock size={11} /> Next Reassessment
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
                <RefreshCw size={12} /> Reassess Now
              </button>
            )}
          </div>
        )}

        {/* Agent metadata */}
        <div className="text-xs text-gray-700 border-t border-gov-700 pt-2 flex justify-between">
          <span>{isFallback ? 'Deterministic fallback' : agent.provider}</span>
          <span className="font-mono">{isFallback ? 'phase3-engine' : agent.model}</span>
        </div>

        {/* Limitations */}
        <div>
          <button
            onClick={() => setShowLimitations(!showLimitations)}
            className="text-xs text-gray-600 hover:text-gray-400 flex items-center gap-1"
          >
            {showLimitations ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            View limitations
          </button>
          {showLimitations && (
            <ul className="mt-2 space-y-1">
              {decision.limitations.map((l, i) => (
                <li key={i} className="text-xs text-gray-600 flex gap-1.5">
                  <span>•</span><span>{l}</span>
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
  const deterministicActions = (result?.agent_context?.government_actions as string[]) || [];

  return (
    <div className="card border border-blue-800 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap size={14} className="text-blue-400" />
          <span className="text-sm font-bold text-blue-300 uppercase tracking-wide">
            CIVICHEAT AI
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs bg-green-900/50 text-green-400 border border-green-800 px-2 py-0.5 rounded font-mono">
            ● NEMOTRON READY
          </span>
          {onClose && (
            <button onClick={onClose} className="text-gray-500 hover:text-gray-300">
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {isError && (
        <div className="bg-red-900/30 border border-red-700 rounded p-2">
          <p className="text-xs text-red-300">⚠ Agent error — try again</p>
        </div>
      )}

      {/* Prompt */}
      {onAsk && (
        <button
          onClick={() => onAsk('What should the government do right now?')}
          className="btn-primary w-full flex items-center justify-center gap-2 text-sm"
          disabled={!result}
        >
          <Zap size={13} />
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

      {/* Deterministic actions preview */}
      {deterministicActions.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1.5 flex items-center gap-1">
            <AlertTriangle size={10} />
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
              Click Ask CIVICHEAT for Nemotron-powered analysis
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
          >
            {showLimitations ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            View data limitations
          </button>
          {showLimitations && (
            <ul className="mt-2 space-y-1">
              {result.data_limitations.map((l, i) => (
                <li key={i} className="text-xs text-gray-600 flex gap-1.5">
                  <span>•</span><span>{l}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
