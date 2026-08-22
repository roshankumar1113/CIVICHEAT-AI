import { useState, useCallback } from 'react';
import { api } from '../services/api';
import type { ReassessmentResponse } from '../types';

export type HeatWatchStatus = 'idle' | 'loading' | 'done' | 'error';

/**
 * HeatWatch reassessment hook.
 *
 * Calls POST /api/reassessment/run, which runs a fresh FortyGuard → Risk →
 * Priority pipeline, compares it against the previous stored snapshot, and
 * (only on meaningful change) invokes Nemotron for an updated recommendation.
 *
 * All values surfaced come straight from the backend response — nothing is
 * fabricated on the client.
 */
export function useReassessment() {
  const [response, setResponse] = useState<ReassessmentResponse | null>(null);
  const [status, setStatus] = useState<HeatWatchStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (city: string, date: string, demoMode: boolean) => {
    try {
      setStatus('loading');
      setError(null);
      const data = await api.runReassessment({
        city,
        date,
        demo_mode: demoMode,
        invoke_nemotron_on_change: true,
      });
      setResponse(data);
      setStatus('done');
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Reassessment failed';
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

  return { response, status, error, run, reset };
}
