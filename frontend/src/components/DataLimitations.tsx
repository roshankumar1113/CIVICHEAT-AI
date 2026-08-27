/**
 * DATA & AI LIMITATIONS — expandable honesty section. §14
 *
 * These bullets are fixed application-level disclaimers (not backend values), so
 * they are stated verbatim. They apply whether or not an analysis has run, which
 * is why this section is always available rather than gated on a result.
 */
import { useState } from 'react';
import { ChevronDown, ChevronUp, ShieldAlert } from 'lucide-react';

const LIMITATIONS: string[] = [
  'CIVICHEAT risk score is application-defined.',
  'Risk score is not medically validated.',
  'FortyGuard data represents available temperature intelligence for the requested analysis.',
  'AI recommendations are decision support.',
  'Recommendations require appropriate official review.',
  'Simulation values, when introduced, must be labeled as estimated/demo assumptions.',
];

export function DataLimitations() {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gov-600 rounded-lg bg-gov-800/60">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2 flex items-center justify-between text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg"
        aria-expanded={expanded}
        aria-controls="data-ai-limitations"
      >
        <span className="flex items-center gap-1.5 text-xs font-bold text-gray-400 uppercase tracking-widest">
          <ShieldAlert size={12} className="text-gray-500" aria-hidden="true" />
          Data &amp; AI Limitations
        </span>
        {expanded ? (
          <ChevronUp size={13} className="text-gray-500" aria-hidden="true" />
        ) : (
          <ChevronDown size={13} className="text-gray-500" aria-hidden="true" />
        )}
      </button>

      {expanded && (
        <ul id="data-ai-limitations" className="px-3 pb-3 pt-0.5 space-y-1.5 border-t border-gov-700">
          {LIMITATIONS.map((item) => (
            <li key={item} className="text-xs text-gray-400 flex items-start gap-1.5 leading-snug">
              <span className="text-gray-600 mt-0.5 flex-shrink-0" aria-hidden="true">•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
