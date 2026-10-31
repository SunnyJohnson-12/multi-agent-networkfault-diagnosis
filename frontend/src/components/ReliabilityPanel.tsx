import React, { useState, useEffect } from 'react';
import { CalibrationReport } from '../types';
import { fetchCalibration } from '../services/api';
import { Target, CheckCircle2, AlertTriangle, RefreshCw, BarChart3, Grid, ShieldCheck } from 'lucide-react';

export const ReliabilityPanel: React.FC = () => {
  const [report, setReport] = useState<CalibrationReport | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    setLoading(true);
    fetchCalibration()
      .then((data) => setReport(data))
      .catch((err) => console.error('Failed to load calibration report:', err))
      .finally(() => setLoading(false));
  }, []);

  const handleRerun = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/calibration/run?runs=60&seed=42', { method: 'POST' });
      const data = await res.json();
      setReport(data);
    } catch (err) {
      console.error('Failed to re-run calibration:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="noc-card" style={{ padding: '24px', textAlign: 'center' }}>
        <div style={{ color: 'var(--accent-cyan)', fontSize: '0.9rem', marginBottom: '8px' }}>
          Running Monte Carlo calibration evaluations across 60 randomized variants...
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
          Measuring Expected Calibration Error (ECE), bin reliability, and abstention behavior.
        </div>
      </div>
    );
  }

  if (!report) return null;

  return (
    <div className="noc-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Target size={20} style={{ color: 'var(--accent-cyan)' }} />
          <div>
            <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, letterSpacing: '0.03em' }}>
              CALIBRATED CONFIDENCE & RELIABILITY BENCHMARK
            </h3>
            <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Quantitative measurement proving that reported confidence scores align with true empirical accuracy
            </p>
          </div>
        </div>

        <button
          onClick={handleRerun}
          disabled={loading}
          style={{
            backgroundColor: '#111827',
            border: '1px solid var(--border-subtle)',
            color: 'var(--accent-cyan)',
            borderRadius: '6px',
            padding: '6px 14px',
            fontSize: '0.75rem',
            fontWeight: 600,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <RefreshCw size={14} /> Re-Evaluate Monte Carlo (60 Runs)
        </button>
      </div>

      {/* Headline Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
        <div style={{ backgroundColor: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '12px 14px' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>OVERALL ACCURACY</div>
          <div className="font-mono" style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--status-green)' }}>
            {(report.overall_accuracy * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: '0.675rem', color: 'var(--text-secondary)' }}>Across all 6 ground-truth fault classes</div>
        </div>

        <div style={{ backgroundColor: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '12px 14px' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>EXPECTED CALIBRATION ERROR (ECE)</div>
          <div className="font-mono" style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
            {report.expected_calibration_error.toFixed(3)}
          </div>
          <div style={{ fontSize: '0.675rem', color: 'var(--text-secondary)' }}>10-bin confidence gap metric (lower is better)</div>
        </div>

        <div style={{ backgroundColor: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '12px 14px' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>CONFIDENCE ON CORRECT</div>
          <div className="font-mono" style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
            {(report.mean_confidence_correct * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: '0.675rem', color: 'var(--text-secondary)' }}>High certainty when diagnosis is sound</div>
        </div>

        <div style={{ backgroundColor: '#0a0f1d', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '12px 14px' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>CONFIDENCE ON INCORRECT</div>
          <div className="font-mono" style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--status-amber)' }}>
            {(report.mean_confidence_incorrect * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: '0.675rem', color: 'var(--text-secondary)' }}>Uncertainty flags potential errors (honest abstention)</div>
        </div>
      </div>

      {/* Grid: Reliability Diagram + Confusion Matrix */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
        {/* Reliability Diagram (10 Bins) */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '10px' }}>
            <BarChart3 size={16} style={{ color: 'var(--accent-cyan)' }} />
            RELIABILITY DIAGRAM (PREDICTED CONFIDENCE VS EMPIRICAL ACCURACY)
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
              <thead>
                <tr style={{ backgroundColor: '#0a0f1d', color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)' }}>
                  <th style={{ padding: '6px 8px', textAlign: 'center' }}>Bin</th>
                  <th style={{ padding: '6px 8px', textAlign: 'right' }}>Samples</th>
                  <th style={{ padding: '6px 8px', textAlign: 'right' }}>Mean Conf</th>
                  <th style={{ padding: '6px 8px', textAlign: 'right' }}>Accuracy</th>
                  <th style={{ padding: '6px 8px', textAlign: 'left' }}>Visual Alignment</th>
                </tr>
              </thead>
              <tbody>
                {report.reliability_diagram.map((b, idx) => {
                  const confPct = Math.round(b.mean_confidence * 100);
                  const accPct = Math.round(b.empirical_accuracy * 100);
                  return (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '6px 8px', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>
                        {b.bin_range}
                      </td>
                      <td style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--text-secondary)' }}>
                        {b.sample_count}
                      </td>
                      <td style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                        {b.sample_count > 0 ? `${confPct}%` : '-'}
                      </td>
                      <td style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--status-green)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                        {b.sample_count > 0 ? `${accPct}%` : '-'}
                      </td>
                      <td style={{ padding: '6px 8px', width: '140px' }}>
                        {b.sample_count > 0 ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <div style={{ flex: 1, backgroundColor: '#111827', height: '10px', borderRadius: '2px', position: 'relative' }}>
                              <div style={{ width: `${confPct}%`, height: '100%', backgroundColor: 'var(--accent-cyan)', borderRadius: '2px', opacity: 0.6 }} />
                              <div style={{ position: 'absolute', top: 0, left: 0, width: `${accPct}%`, height: '100%', backgroundColor: 'var(--status-green)', borderRadius: '2px' }} />
                            </div>
                          </div>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>No samples</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Confusion Matrix Heatmap */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '10px' }}>
            <Grid size={16} style={{ color: 'var(--accent-cyan)' }} />
            CONFUSION MATRIX (GROUND TRUTH VS SYSTEM DIAGNOSIS)
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.725rem' }}>
              <thead>
                <tr style={{ backgroundColor: '#0a0f1d', color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)' }}>
                  <th style={{ padding: '6px 8px', textAlign: 'left' }}>Truth \ Pred</th>
                  {Object.keys(report.confusion_matrix).map((k) => (
                    <th key={k} style={{ padding: '6px 8px', textAlign: 'center', textTransform: 'capitalize' }}>
                      {k.slice(0, 4)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(report.confusion_matrix).map(([truth, preds]) => (
                  <tr key={truth} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
                      {truth}
                    </td>
                    {Object.keys(report.confusion_matrix).map((predK) => {
                      const count = preds[predK] || 0;
                      const isDiagonal = truth === predK;
                      return (
                        <td
                          key={predK}
                          style={{
                            padding: '6px 8px',
                            textAlign: 'center',
                            fontFamily: 'var(--font-mono)',
                            backgroundColor: isDiagonal && count > 0 ? 'rgba(34, 197, 94, 0.2)' : count > 0 ? 'rgba(239, 68, 68, 0.2)' : 'transparent',
                            color: isDiagonal && count > 0 ? 'var(--status-green)' : count > 0 ? 'var(--status-red)' : 'var(--text-muted)',
                            fontWeight: count > 0 ? 700 : 400,
                          }}
                        >
                          {count}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
