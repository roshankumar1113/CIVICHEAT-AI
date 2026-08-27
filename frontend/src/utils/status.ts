import type { IntegrationStatus } from '../types';

/**
 * Single source of truth for how observed integration state is presented.
 *
 * The dashboard shows CONNECTED / LIVE only when the backend reports that a
 * real call actually succeeded (state === 'CONNECTED'). Anything else is
 * reported honestly — never upgraded to look healthier than it is.
 */

export type Tone = 'ok' | 'warn' | 'bad' | 'idle';

export interface StatusChip {
  /** Short uppercase value, e.g. 'CONNECTED', 'FALLBACK', 'DISCONNECTED'. */
  value: string;
  tone: Tone;
  /** Plain-language explanation shown on hover and in the system status list. */
  detail: string;
}

export const TONE_TEXT: Record<Tone, string> = {
  ok: 'text-green-300',
  warn: 'text-yellow-300',
  bad: 'text-red-300',
  idle: 'text-gray-400',
};

export const TONE_DOT: Record<Tone, string> = {
  ok: 'bg-green-400',
  warn: 'bg-yellow-400',
  bad: 'bg-red-500',
  idle: 'bg-gray-500',
};

export const TONE_CHIP: Record<Tone, string> = {
  ok: 'bg-green-900/60 text-green-300 border-green-700',
  warn: 'bg-yellow-900/60 text-yellow-300 border-yellow-700',
  bad: 'bg-red-900/60 text-red-300 border-red-700',
  idle: 'bg-gov-700 text-gray-400 border-gov-500',
};

const UNKNOWN: StatusChip = {
  value: 'UNKNOWN',
  tone: 'idle',
  detail: 'Backend has not reported this integration yet.',
};

/**
 * FortyGuard reduces to CONNECTED / DISCONNECTED, per the command-center spec.
 * DEGRADED and TIMEOUT are surfaced with their own detail text but still count
 * as not-connected, because the data on screen did not come from FortyGuard.
 */
export function fortyguardChip(s: IntegrationStatus | null | undefined): StatusChip {
  if (!s) return UNKNOWN;
  switch (s.state) {
    case 'CONNECTED':
      return {
        value: 'CONNECTED',
        tone: 'ok',
        detail: s.detail ?? 'A FortyGuard request has succeeded this session.',
      };
    case 'NOT_CONFIGURED':
      return {
        value: 'DISCONNECTED',
        tone: 'bad',
        detail: 'FORTYGUARD_API_KEY is not configured. Demonstration data only.',
      };
    case 'UNVERIFIED':
      return {
        value: 'DISCONNECTED',
        tone: 'idle',
        detail: 'Credentials present but no FortyGuard request attempted yet.',
      };
    case 'TIMEOUT':
      return {
        value: 'DISCONNECTED',
        tone: 'bad',
        detail: s.detail ?? 'The last FortyGuard request timed out.',
      };
    case 'AUTH_ERROR':
      return {
        value: 'DISCONNECTED',
        tone: 'bad',
        detail: s.detail ?? 'FortyGuard rejected the configured credentials.',
      };
    default:
      return {
        value: 'DISCONNECTED',
        tone: 'bad',
        detail: s.detail ?? 'The last FortyGuard request did not succeed.',
      };
  }
}

/**
 * Nemotron is a three-state indicator: LIVE (model answered), FALLBACK (model
 * reachable-but-unusable, deterministic engine in use), DISCONNECTED.
 */
export function nemotronChip(s: IntegrationStatus | null | undefined): StatusChip {
  if (!s) return UNKNOWN;
  switch (s.state) {
    case 'CONNECTED':
      return {
        value: 'LIVE',
        tone: 'ok',
        detail: s.detail ?? 'Nemotron returned a usable response this session.',
      };
    case 'DEGRADED':
      return {
        value: 'FALLBACK',
        tone: 'warn',
        detail:
          s.detail ??
          'Nemotron responded but the payload was unusable. Deterministic engine in use.',
      };
    case 'TIMEOUT':
      return {
        value: 'FALLBACK',
        tone: 'warn',
        detail: s.detail ?? 'Nemotron timed out. Deterministic engine in use.',
      };
    case 'AUTH_ERROR':
      return {
        value: 'FALLBACK',
        tone: 'warn',
        detail: s.detail ?? 'Nemotron rejected the API key. Deterministic engine in use.',
      };
    case 'UNAVAILABLE':
      return {
        value: 'FALLBACK',
        tone: 'warn',
        detail: s.detail ?? 'Nemotron returned an error. Deterministic engine in use.',
      };
    case 'NOT_CONFIGURED':
      return {
        value: 'DISCONNECTED',
        tone: 'bad',
        detail: 'NEMOTRON_BASE_URL or NEMOTRON_API_KEY is not configured.',
      };
    case 'UNVERIFIED':
      return {
        value: 'DISCONNECTED',
        tone: 'idle',
        detail: 'Credentials present but no inference call attempted yet.',
      };
    default:
      return UNKNOWN;
  }
}

/** Wording used everywhere the LIVE / DEMO distinction is shown. §3 */
export const DATA_MODE_COPY = {
  DEMO: 'Using deterministic demonstration data.',
  LIVE: 'Temperature intelligence retrieved from FortyGuard.',
} as const;
