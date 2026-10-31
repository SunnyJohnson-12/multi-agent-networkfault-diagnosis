import React from 'react';
import { ToggleLeft, ToggleRight, AlertOctagon, HelpCircle } from 'lucide-react';

interface MissingAgentToggleProps {
  disabledAgents: string[];
  onToggleAgent: (agentName: string) => void;
  isLoading: boolean;
}

export const MissingAgentToggle: React.FC<MissingAgentToggleProps> = ({
  disabledAgents,
  onToggleAgent,
  isLoading,
}) => {
  const agents = [
    {
      id: 'performance_agent',
      label: 'Performance Agent',
      desc: 'Monitors latency, packet loss, bandwidth & link utilization',
    },
    {
      id: 'infrastructure_agent',
      label: 'Infrastructure Agent',
      desc: 'Monitors CPU, RAM, interface errors & hardware queue drops',
    },
    {
      id: 'connectivity_agent',
      label: 'Connectivity Agent',
      desc: 'Monitors campus topology graph, blast radius & shared uplinks',
    },
  ];

  return (
    <div className="noc-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertOctagon size={18} style={{ color: 'var(--accent-cyan)' }} />
          <span style={{ fontSize: '0.85rem', fontWeight: 600, letterSpacing: '0.04em' }}>
            "WHAT IF AN AGENT WERE MISSING?" (MULTI-AGENT COLLABORATION TEST)
          </span>
        </div>
        <span className="badge badge-amber" style={{ fontSize: '0.675rem' }}>
          COLLABORATION PROOF
        </span>
      </div>

      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '12px', lineHeight: 1.4 }}>
        Toggle any domain agent off to test resilient degraded-mode correlation. Watch how diagnostic confidence drops and runner-up hypotheses shift in real-time.
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px' }}>
        {agents.map((ag) => {
          const isDisabled = disabledAgents.includes(ag.id);

          return (
            <div
              key={ag.id}
              onClick={() => !isLoading && onToggleAgent(ag.id)}
              style={{
                backgroundColor: isDisabled ? 'rgba(239, 68, 68, 0.08)' : 'rgba(16, 26, 46, 0.6)',
                border: isDisabled ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '10px 12px',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                transition: 'all 0.2s ease',
              }}
            >
              <div>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: isDisabled ? 'var(--status-red)' : '#fff' }}>
                  {ag.label}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  {ag.desc}
                </div>
              </div>

              <div style={{ color: isDisabled ? 'var(--status-red)' : 'var(--status-green)', paddingLeft: '8px' }}>
                {isDisabled ? <ToggleLeft size={24} /> : <ToggleRight size={24} />}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
