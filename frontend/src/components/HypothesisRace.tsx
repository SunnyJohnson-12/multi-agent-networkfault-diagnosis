import React from 'react';
import { HypothesisScore } from '../types';
import { Award, AlertCircle, Check, HelpCircle } from 'lucide-react';

interface HypothesisRaceProps {
  hypotheses: HypothesisScore[];
  status: string;
}

export const HypothesisRace: React.FC<HypothesisRaceProps> = ({ hypotheses, status }) => {
  if (!hypotheses || hypotheses.length === 0) {
    return (
      <div className="noc-card" style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)' }}>
        No hypothesis rankings available.
      </div>
    );
  }

  const topScore = hypotheses[0]?.score || 0;
  const runnerUpScore = hypotheses[1]?.score || 0;
  const margin = topScore - runnerUpScore;
  const isAmbiguous = status === 'ambiguous' || (margin <= 0.12 && status !== 'no_fault_detected' && status !== 'insufficient_evidence');
  const isInsufficient = status === 'insufficient_evidence';
  const isNoFault = status === 'no_fault_detected';

  return (
    <div className="noc-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Award size={18} style={{ color: 'var(--accent-cyan)' }} />
          <span style={{ fontSize: '0.85rem', fontWeight: 600, letterSpacing: '0.04em' }}>
            HYPOTHESIS RACE (COMPETING ROOT-CAUSE CONVERGENCE)
          </span>
        </div>

        {isInsufficient ? (
          <span className="badge badge-amber" style={{ fontSize: '0.7rem' }}>
            <AlertCircle size={12} /> INSUFFICIENT TELEMETRY
          </span>
        ) : isAmbiguous ? (
          <span className="badge badge-amber" style={{ fontSize: '0.7rem' }}>
            <AlertCircle size={12} /> AMBIGUOUS (MARGIN: {(margin * 100).toFixed(0)}%)
          </span>
        ) : isNoFault ? (
          <span className="badge badge-cyan" style={{ fontSize: '0.7rem' }}>
            <Check size={12} /> NOMINAL (NO FAULT)
          </span>
        ) : (
          <span className="badge badge-green" style={{ fontSize: '0.7rem' }}>
            <Check size={12} /> CONVERGED (LEAD: +{(margin * 100).toFixed(0)}%)
          </span>
        )}
      </div>

      {/* Race Bars */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {hypotheses.map((h, idx) => {
          const isWinner = idx === 0;
          const isRunnerUp = idx === 1;
          const scorePct = Math.round(h.score * 100);

          let barColor = 'var(--accent-blue)';
          if (isWinner) {
            barColor = isAmbiguous ? 'var(--status-amber)' : 'var(--status-green)';
          } else if (isRunnerUp && isAmbiguous) {
            barColor = 'var(--status-orange)';
          } else {
            barColor = 'rgba(56, 189, 248, 0.4)';
          }

          return (
            <div key={h.hypothesis} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.775rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span
                    className="font-mono"
                    style={{
                      color: isWinner ? 'var(--accent-cyan)' : 'var(--text-muted)',
                      fontWeight: 700,
                    }}
                  >
                    #{idx + 1}
                  </span>
                  <span style={{ fontWeight: isWinner ? 600 : 400, color: isWinner ? '#fff' : 'var(--text-secondary)' }}>
                    {h.hypothesis}
                  </span>
                </div>
                <span className="font-mono" style={{ fontWeight: 700, color: barColor }}>
                  {h.score.toFixed(2)} ({scorePct}%)
                </span>
              </div>

              {/* Score Bar Track */}
              <div
                style={{
                  height: '7px',
                  backgroundColor: '#111827',
                  borderRadius: '4px',
                  overflow: 'hidden',
                  position: 'relative',
                }}
              >
                <div
                  style={{
                    width: `${scorePct}%`,
                    height: '100%',
                    backgroundColor: barColor,
                    borderRadius: '4px',
                    transition: 'width 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
                  }}
                />
              </div>

              {/* Signals Explanation */}
              {h.matched_signals && h.matched_signals.length > 0 && (
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {h.matched_signals.slice(0, 2).map((sig, sidx) => (
                    <span
                      key={sidx}
                      style={{
                        backgroundColor: 'rgba(56, 189, 248, 0.08)',
                        padding: '1px 6px',
                        borderRadius: '3px',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      ✓ {sig}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
