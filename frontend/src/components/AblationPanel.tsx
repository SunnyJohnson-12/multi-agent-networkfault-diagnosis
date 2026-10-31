import React, { useState, useEffect } from 'react';
import { AblationReport } from '../types';
import { fetchAblation } from '../services/api';
import { GitCompare, AlertTriangle, ShieldCheck, ArrowDownRight, Layers, Sparkles } from 'lucide-react';

interface AblationPanelProps {
  sessionId: string | undefined;
  onSelectDisabledAgent?: (agentName: string) => void;
}

export const AblationPanel: React.FC<AblationPanelProps> = ({ sessionId, onSelectDisabledAgent }) => {
  const [ablation, setAblation] = useState<AblationReport | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    let isMounted = true;
    setLoading(true);
    fetchAblation(sessionId)
      .then((data) => {
        if (isMounted) setAblation(data);
      })
      .catch((err) => console.error('Failed to load ablation report:', err))
      .finally(() => {
        if (isMounted) setLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [sessionId]);

  if (loading) {
    return (
      <div className="noc-card" style={{ padding: '24px', textAlign: 'center' }}>
        <div style={{ color: 'var(--accent-cyan)', fontSize: '0.9rem', marginBottom: '8px' }}>
          Running isolated ablation runs across all agent configurations...
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
          Proving multi-agent collaboration by measuring marginal contribution per agent.
        </div>
      </div>
    );
  }

  if (!ablation) {
    return (
      <div className="noc-card" style={{ padding: '20px', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          Select or run a diagnostic session to view the Agent Ablation Collaboration Proof.
        </p>
      </div>
    );
  }

  return (
    <div className="noc-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <GitCompare size={20} style={{ color: 'var(--accent-cyan)' }} />
          <div>
            <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, letterSpacing: '0.03em' }}>
              AGENT ABLATION ANALYSIS (PROOF OF REAL COLLABORATION)
            </h3>
            <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Quantitative proof that removing any single domain agent alters the diagnostic consensus
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge badge-green" style={{ fontSize: '0.7rem' }}>
            <ShieldCheck size={12} /> COLLABORATION PROVEN
          </span>
          <span className="badge badge-cyan" style={{ fontSize: '0.7rem' }}>
            MOST CRITICAL: {ablation.most_critical_agent.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Summary Banner */}
      <div
        style={{
          backgroundColor: 'rgba(56, 189, 248, 0.08)',
          border: '1px solid rgba(56, 189, 248, 0.3)',
          borderRadius: '6px',
          padding: '12px 16px',
          fontSize: '0.825rem',
          color: 'var(--text-primary)',
          lineHeight: 1.5,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '4px' }}>
          <Sparkles size={14} /> Consensus Proof Summary
        </div>
        {ablation.summary}
      </div>

      {/* Grouped Bar Chart Comparison */}
      <div>
        <div style={{ fontSize: '0.775rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '10px' }}>
          CONFIDENCE COMPARISON PER ABLATED CONFIGURATION
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {ablation.configurations.map((cfg, idx) => {
            const isBaseline = cfg.config.includes('Baseline');
            const pct = Math.round(cfg.confidence * 100);
            return (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ width: '180px', fontSize: '0.75rem', color: isBaseline ? 'var(--accent-cyan)' : 'var(--text-secondary)', fontWeight: isBaseline ? 700 : 500 }}>
                  {cfg.config}
                </div>
                <div style={{ flex: 1, backgroundColor: '#0a0f1d', borderRadius: '4px', height: '22px', position: 'relative', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${pct}%`,
                      backgroundColor: isBaseline ? 'var(--status-green)' : pct >= 70 ? 'var(--accent-blue)' : pct >= 50 ? 'var(--status-amber)' : 'var(--status-red)',
                      transition: 'width 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
                      borderRadius: '3px',
                    }}
                  />
                  <div
                    style={{
                      position: 'absolute',
                      right: '8px',
                      top: '2px',
                      fontSize: '0.75rem',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 700,
                      color: '#fff',
                    }}
                  >
                    {pct}% ({cfg.status.toUpperCase()})
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Marginal Contribution Table */}
      <div>
        <div style={{ fontSize: '0.775rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
          PER-AGENT MARGINAL CONTRIBUTION & VERDICT
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.775rem' }}>
            <thead>
              <tr style={{ backgroundColor: '#0a0f1d', color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)' }}>
                <th style={{ padding: '8px 10px', textAlign: 'left' }}>Ablated Agent</th>
                <th style={{ padding: '8px 10px', textAlign: 'center' }}>Confidence Drop</th>
                <th style={{ padding: '8px 10px', textAlign: 'center' }}>Root Cause Shift</th>
                <th style={{ padding: '8px 10px', textAlign: 'center' }}>Degraded</th>
                <th style={{ padding: '8px 10px', textAlign: 'left' }}>Lost Evidence</th>
                <th style={{ padding: '8px 10px', textAlign: 'left' }}>Ablation Verdict</th>
              </tr>
            </thead>
            <tbody>
              {ablation.agent_contributions.map((c, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '8px 10px', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                    {c.agent_name}
                  </td>
                  <td style={{ padding: '8px 10px', textAlign: 'center', fontFamily: 'var(--font-mono)', color: c.confidence_delta > 0.1 ? 'var(--status-red)' : 'var(--status-amber)' }}>
                    -{Math.round(c.confidence_delta * 100)}%
                  </td>
                  <td style={{ padding: '8px 10px', textAlign: 'center' }}>
                    {c.root_cause_changed ? (
                      <span className="badge badge-amber" style={{ fontSize: '0.65rem' }}>SHIFTED</span>
                    ) : (
                      <span className="badge" style={{ fontSize: '0.65rem', backgroundColor: '#111827', color: 'var(--text-muted)' }}>UNCHANGED</span>
                    )}
                  </td>
                  <td style={{ padding: '8px 10px', textAlign: 'center' }}>
                    {c.status_degraded ? (
                      <span className="badge badge-red" style={{ fontSize: '0.65rem' }}>AMBIGUOUS</span>
                    ) : (
                      <span className="badge badge-green" style={{ fontSize: '0.65rem' }}>DIAGNOSED</span>
                    )}
                  </td>
                  <td style={{ padding: '8px 10px', color: 'var(--text-secondary)' }}>
                    {c.lost_evidence.length > 0 ? c.lost_evidence.map((e) => `[${e}]`).join(' ') : 'None'}
                  </td>
                  <td style={{ padding: '8px 10px', color: 'var(--text-primary)', fontStyle: 'italic' }}>
                    "{c.verdict}"
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
