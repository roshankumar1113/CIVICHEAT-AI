import { useState, useCallback } from 'react';
import { api } from '../services/api';
import type { AgentResponse, ActionPlanResponse } from '../types';

export type AgentStatus = 'idle' | 'loading' | 'done' | 'error';

export function useAgent() {
  const [response, setResponse] = useState<AgentResponse | null>(null);
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  const ask = useCallback(async (
    message: string,
    city: string,
    date: string,
    demoMode: boolean,
  ) => {
    try {
      setStatus('loading');
      setError(null);
      setResponse(null);
      const data = await api.agentAnalyze({ message, city, date, demo_mode: demoMode });
      setResponse(data);
      setStatus('done');
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Agent request failed';
      setError(msg);
      setStatus('error');
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    setResponse(null);
    setStatus('idle');
    setError(null);
  }, []);

  return { response, status, error, ask, reset };
}

export function useActionPlan() {
  const [plan, setPlan] = useState<ActionPlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async (
    zoneId: string,
    city: string,
    date: string,
    demoMode: boolean,
  ) => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.agentActionPlan({ zone_id: zoneId, city, date, demo_mode: demoMode });
      setPlan(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action plan failed');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { plan, loading, error, fetch };
}
