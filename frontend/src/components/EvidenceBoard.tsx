import React from 'react';
import { SupportingEvidenceItem } from '../types';
import { ClipboardList, Layers } from 'lucide-react';

interface EvidenceBoardProps {
  evidence: SupportingEvidenceItem[];
  sources: string[];
  onHoverDevice: (deviceId: string | null) => void;
}

export const EvidenceBoard: React.FC<EvidenceBoardProps> = ({
  evidence,
  sources,
  onHoverDevice,
}) => {
  return (
    <div className="noc-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ClipboardList size={18} style={{ color: 'var(--accent-cyan)' }} />
          <span style={{ fontSize: '0.85rem', fontWeight: 600, letterSpacing: '0.04em' }}>
            CORROBORATING EVIDENCE BOARD
          </span>
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          {sources.map((src) => (
            <span key={src} className="badge badge-cyan" style={{ fontSize: '0.625rem' }}>
              {src.replace('_agent', '')}
            </span>
          ))}
        </div>
      </div>

      {/* Cards Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
          gap: '10px',
          maxHeight: '320px',
          overflowY: 'auto',
          paddingRight: '4px',
        }}
      >
        {evidence.map((ev, idx) => {
          return (
            <div
              key={`${ev.metric}-${idx}`}
              onMouseEnter={() => {
                // If interpretation contains a device identifier, highlight it
                const match = ev.interpretation.match(/\b(HOSTEL_[A-Z0-9_]+|ACAD_[A-Z0-9_]+|LIB_[A-Z0-9_]+|DC_[A-Z0-9_]+)\b/);
                if (match) {
                  onHoverDevice(match[1]);
                }
              }}
              onMouseLeave={() => onHoverDevice(null)}
              style={{
                backgroundColor: 'rgba(16, 26, 46, 0.7)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '10px 12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
                transition: 'all 0.2s ease',
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent-blue)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-subtle)';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span className="font-mono" style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent-blue)' }}>
                  {ev.metric}
                </span>
                <span
                  className="font-mono"
                  style={{
                    fontSize: '0.85rem',
                    fontWeight: 700,
                    color: '#fff',
                    backgroundColor: '#111827',
                    padding: '2px 6px',
                    borderRadius: '4px',
                  }}
                >
                  {String(ev.value)}
                </span>
              </div>

              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.35 }}>
                {ev.interpretation}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
