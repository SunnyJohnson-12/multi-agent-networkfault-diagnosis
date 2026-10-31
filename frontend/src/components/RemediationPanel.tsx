import React from 'react';
import { SimulatedRemediation } from '../types';
import { Wrench, ArrowRight, AlertTriangle, ShieldCheck } from 'lucide-react';

interface RemediationPanelProps {
  remediation: SimulatedRemediation | null | undefined;
}

export const RemediationPanel: React.FC<RemediationPanelProps> = ({ remediation }) => {
  if (!remediation) return null;

  return (
    <div className="noc-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Wrench size={18} style={{ color: 'var(--accent-cyan)' }} />
          <span style={{ fontSize: '0.85rem', fontWeight: 600, letterSpacing: '0.04em' }}>
            SIMULATED REMEDIATION (PROJECTED IMPACT)
          </span>
        </div>
        <span className="badge badge-amber" style={{ fontSize: '0.65rem' }}>
          SIMULATION ONLY
        </span>
      </div>

      {/* Main card */}
      <div
        style={{
          backgroundColor: 'rgba(56, 189, 248, 0.05)',
          border: '1px solid rgba(56, 189, 248, 0.2)',
          borderRadius: '6px',
          padding: '12px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
        }}
      >
        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-blue)' }}>
          {remediation.action_type}
        </div>

        <div style={{ fontSize: '0.775rem', color: 'var(--text-secondary)' }}>
          {remediation.description}
        </div>

        {/* Before vs After Metric Comparison */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            backgroundColor: '#0a0f1d',
            padding: '10px 14px',
            borderRadius: '6px',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div>
            <div style={{ fontSize: '0.675rem', color: 'var(--text-muted)' }}>CURRENT (PRE-REMEDIATION)</div>
            <div className="font-mono" style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--status-red)' }}>
              {String(remediation.pre_remediation_value)}
            </div>
          </div>

          <ArrowRight size={18} style={{ color: 'var(--text-muted)' }} />

          <div>
            <div style={{ fontSize: '0.675rem', color: 'var(--text-muted)' }}>PROJECTED (POST-REMEDIATION)</div>
            <div className="font-mono" style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--status-green)' }}>
              {String(remediation.post_remediation_value)}
            </div>
          </div>
        </div>

        <div style={{ fontSize: '0.75rem', color: 'var(--text-primary)', fontStyle: 'italic' }}>
          "{remediation.estimated_impact}"
        </div>

        <div
          style={{
            fontSize: '0.7rem',
            color: 'var(--status-amber)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            borderTop: '1px solid var(--border-subtle)',
            paddingTop: '8px',
          }}
        >
          <AlertTriangle size={14} />
          <span>{remediation.disclaimer}</span>
        </div>
      </div>
    </div>
  );
};
