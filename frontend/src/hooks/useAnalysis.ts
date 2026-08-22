import { useState, useCallback } from 'react';
import { api } from '../services/api';
import type { AnalyzeResponse } from '../types';

export function useAnalysis() {
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (city: string, date: string, demoMode: boolean) => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.analyze({ city, date, demo_mode: demoMode });
      setResult(data);
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Analysis failed';
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, loading, error, run, reset };
}
