import React from 'react';
import { FinalDiagnosisReport, ScenarioItem } from '../types';
import { Activity, ShieldAlert, Cpu, Share2, Play, RefreshCw, Eye } from 'lucide-react';

interface HeaderBarProps {
  report: FinalDiagnosisReport | null;
  scenarios: ScenarioItem[];
  selectedScenario: string;
  onSelectScenario: (scenarioFile: string) => void;
  onRunDiagnosis: () => void;
  isLoading: boolean;
  onOpenDemoMode: () => void;
}

export const HeaderBar: React.FC<HeaderBarProps> = ({
  report,
  scenarios,
  selectedScenario,
  onSelectScenario,
  onRunDiagnosis,
  isLoading,
  onOpenDemoMode,
}) => {
  const confidence = report?.confidence ? Math.round(report.confidence * 100) : 0;
  const status = report?.status || 'idle';
  const severity = report?.extensions?.severity || 'low';
  const messageCount = report?.extensions?.agent_message_count || 0;
  const affectedCount = report?.affected_devices?.length || 0;

  const getSeverityBadgeClass = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return 'badge-red';
      case 'high':
        return 'badge-amber';
      case 'medium':
        return 'badge-amber';
      default:
        return 'badge-green';
    }
  };

  const getStatusBadgeClass = (st: string) => {
    switch (st) {
      case 'diagnosed':
        return 'badge-green';
      case 'ambiguous':
        return 'badge-amber';
      case 'no_fault_detected':
        return 'badge-cyan';
      case 'insufficient_evidence':
        return 'badge-amber';
      default:
        return 'badge-red';
    }
  };

  return (
    <header
      style={{
        backgroundColor: '#090f1d',
        borderBottom: '1px solid var(--border-subtle)',
        padding: '12px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}
    >
      {/* Brand & Incident Info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              backgroundColor: 'var(--accent-cyan)',
              boxShadow: '0 0 10px var(--accent-cyan)',
            }}
          />
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.05rem', fontWeight: 700, letterSpacing: '0.04em' }}>
                THE SIGNAL ROOM
              </span>
              <span className="badge badge-cyan" style={{ fontSize: '0.65rem' }}>
                MULTI-AGENT NOC
              </span>
            </div>
            <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }} className="font-mono">
              CAMPUS NETWORK FAULT DIAGNOSIS
            </div>
            <div style={{ fontSize: '0.65rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
              <span style={{ color: 'var(--status-amber)' }}>⚠️</span>
              <span>Simulation & Diagnostics Only — No Production Changes</span>
            </div>
          </div>
        </div>

        {report && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
              borderLeft: '1px solid var(--border-subtle)',
              paddingLeft: '18px',
            }}
          >
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>INCIDENT ID</div>
              <div className="font-mono" style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
                {report.incident_id}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>STATUS</div>
              <span className={`badge ${getStatusBadgeClass(status)}`}>{status}</span>
            </div>

            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>SEVERITY</div>
              <span className={`badge ${getSeverityBadgeClass(severity)}`}>{severity}</span>
            </div>

            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>CONFIDENCE</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div
                  style={{
                    width: '64px',
                    height: '8px',
                    backgroundColor: '#1e293b',
                    borderRadius: '4px',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${confidence}%`,
                      height: '100%',
                      backgroundColor: confidence >= 80 ? 'var(--status-green)' : confidence >= 60 ? 'var(--status-amber)' : 'var(--status-red)',
                      transition: 'width 0.4s ease',
                    }}
                  />
                </div>
                <span className="font-mono" style={{ fontSize: '0.825rem', fontWeight: 700 }}>
                  {confidence}%
                </span>
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>IMPACTED NODES</div>
              <div className="font-mono" style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                {affectedCount} devices
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>MESSAGES</div>
              <div className="font-mono" style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                {messageCount} msgs
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Control Actions & Scenario Selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Scenario:</span>
          <select
            value={selectedScenario}
            onChange={(e) => onSelectScenario(e.target.value)}
            style={{
              backgroundColor: '#111928',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '0.8rem',
              fontFamily: 'var(--font-mono)',
              outline: 'none',
              cursor: 'pointer',
            }}
          >
            {scenarios.map((s) => (
              <option key={s.file} value={s.file}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={onRunDiagnosis}
          disabled={isLoading}
          style={{
            backgroundColor: isLoading ? '#1e293b' : 'rgba(56, 189, 248, 0.15)',
            color: isLoading ? 'var(--text-muted)' : 'var(--accent-blue)',
            border: '1px solid var(--border-active)',
            borderRadius: '6px',
            padding: '7px 14px',
            fontSize: '0.8rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s',
          }}
        >
          <RefreshCw size={14} className={isLoading ? 'wire-active' : ''} />
          {isLoading ? 'Diagnosing...' : 'Re-Diagnose'}
        </button>

        <button
          onClick={onOpenDemoMode}
          style={{
            backgroundColor: 'rgba(0, 240, 255, 0.15)',
            color: 'var(--accent-cyan)',
            border: '1px solid var(--accent-cyan)',
            borderRadius: '6px',
            padding: '7px 14px',
            fontSize: '0.8rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            cursor: 'pointer',
            transition: 'all 0.2s',
          }}
        >
          <Play size={14} />
          Presenter Mode
        </button>
      </div>
    </header>
  );
};
