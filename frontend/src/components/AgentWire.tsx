import React, { useState } from 'react';
import { AgentMessage } from '../types';
import { Radio, ArrowRight, Zap, Code, CheckCircle, AlertTriangle } from 'lucide-react';

interface AgentWireProps {
  messages: AgentMessage[];
}

export const AgentWire: React.FC<AgentWireProps> = ({ messages }) => {
  const [selectedMessage, setSelectedMessage] = useState<AgentMessage | null>(null);

  const getAgentColor = (agent: string) => {
    switch (agent) {
      case 'orchestrator':
        return 'var(--accent-blue)';
      case 'performance_agent':
        return '#38bdf8';
      case 'infrastructure_agent':
        return '#a855f7';
      case 'connectivity_agent':
        return '#3b82f6';
      case 'correlation_agent':
        return '#f59e0b';
      case 'reporting_agent':
        return '#10b981';
      default:
        return 'var(--text-muted)';
    }
  };

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'clarification_request':
      case 'clarification_response':
        return 'badge-amber';
      case 'diagnostic_finding':
        return 'badge-cyan';
      case 'consolidated_diagnosis':
      case 'final_report':
        return 'badge-green';
      case 'agent_error':
        return 'badge-red';
      default:
        return 'badge-cyan';
    }
  };

  return (
    <div className="noc-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Radio size={18} style={{ color: 'var(--accent-cyan)' }} className="wire-active" />
          <span style={{ fontSize: '0.85rem', fontWeight: 600, letterSpacing: '0.04em' }}>
            AGENT CONVERSATION STREAM ("AGENT WIRE")
          </span>
        </div>
        <span className="badge badge-cyan" style={{ fontSize: '0.7rem' }}>
          {messages.length} PROTOCOL MESSAGES
        </span>
      </div>

      {/* Message List */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          overflowY: 'auto',
          maxHeight: '400px',
          paddingRight: '6px',
        }}
      >
        {messages.map((m, idx) => {
          const isCrossQuery = m.message_type === 'clarification_request' || m.message_type === 'clarification_response';

          return (
            <div
              key={m.message_id || idx}
              onClick={() => setSelectedMessage(m)}
              style={{
                backgroundColor: isCrossQuery ? 'rgba(245, 158, 11, 0.08)' : 'rgba(16, 26, 46, 0.7)',
                border: isCrossQuery ? '1px solid rgba(245, 158, 11, 0.3)' : '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '10px 12px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent-cyan)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = isCrossQuery ? 'rgba(245, 158, 11, 0.3)' : 'var(--border-subtle)';
              }}
            >
              {/* Routing & Metadata */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.725rem' }}>
                  <span className="font-mono" style={{ color: 'var(--text-muted)' }}>
                    #{idx + 1}
                  </span>
                  <span
                    className="font-mono"
                    style={{ fontWeight: 600, color: getAgentColor(m.source_agent) }}
                  >
                    {m.source_agent}
                  </span>
                  <ArrowRight size={12} style={{ color: 'var(--text-muted)' }} />
                  <span
                    className="font-mono"
                    style={{ fontWeight: 600, color: getAgentColor(m.target_agent) }}
                  >
                    {m.target_agent}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  {isCrossQuery && (
                    <span className="badge badge-amber" style={{ fontSize: '0.625rem' }}>
                      <Zap size={10} /> CROSS-QUERY
                    </span>
                  )}
                  <span className={`badge ${getTypeBadge(m.message_type)}`} style={{ fontSize: '0.625rem' }}>
                    {m.message_type}
                  </span>
                </div>
              </div>

              {/* Finding Text */}
              <div style={{ fontSize: '0.8rem', color: 'var(--text-primary)', lineHeight: 1.4 }}>
                {m.finding}
              </div>

              {/* Metric Pill if present */}
              {m.metric && (
                <div style={{ marginTop: '6px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.7rem' }}>
                  <span className="font-mono" style={{ color: 'var(--text-muted)' }}>
                    Metric: <strong style={{ color: 'var(--accent-blue)' }}>{m.metric}</strong>
                  </span>
                  {m.value !== null && m.value !== undefined && (
                    <span className="font-mono" style={{ color: 'var(--text-muted)' }}>
                      Value: <strong style={{ color: '#fff' }}>{String(m.value)} {m.unit}</strong>
                    </span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Raw JSON Inspector Modal */}
      {selectedMessage && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '20px',
          }}
          onClick={() => setSelectedMessage(null)}
        >
          <div
            className="noc-card"
            style={{
              width: '680px',
              maxWidth: '90vw',
              maxHeight: '80vh',
              display: 'flex',
              flexDirection: 'column',
              padding: '20px',
              backgroundColor: '#0a0f1c',
              border: '1px solid var(--accent-cyan)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Code size={18} style={{ color: 'var(--accent-cyan)' }} />
                <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                  PROTOCOL MESSAGE INSPECTOR (UUID: {selectedMessage.message_id.slice(0, 8)}...)
                </span>
              </div>
              <button
                onClick={() => setSelectedMessage(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '1.2rem',
                  cursor: 'pointer',
                }}
              >
                ✕
              </button>
            </div>

            <pre
              className="font-mono"
              style={{
                backgroundColor: '#05080f',
                padding: '14px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                color: '#38bdf8',
                overflowY: 'auto',
                flex: 1,
              }}
            >
              {JSON.stringify(selectedMessage, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
