import React, { useState, useEffect } from 'react';
import { CampusTopology, FinalDiagnosisReport, FaultPreset } from '../types';
import { fetchFaultPresets, injectAndDiagnose } from '../services/api';
import { Zap, Play, RefreshCw, AlertCircle, Sliders, ShieldAlert, CheckCircle2 } from 'lucide-react';

interface ChaosPanelProps {
  topology: CampusTopology | null;
  onDiagnosisComplete: (report: FinalDiagnosisReport) => void;
  isLoading: boolean;
}

export const ChaosPanel: React.FC<ChaosPanelProps> = ({ topology, onDiagnosisComplete, isLoading }) => {
  const [presets, setPresets] = useState<FaultPreset[]>([]);
  const [selectedTarget, setSelectedTarget] = useState<string>('HOSTEL_CORE_SW_01');
  const [utilization, setUtilization] = useState<number>(95);
  const [packetLoss, setPacketLoss] = useState<number>(8.5);
  const [latency, setLatency] = useState<number>(150);
  const [queueDrops, setQueueDrops] = useState<number>(12000);
  const [crcErrors, setCrcErrors] = useState<number>(0);
  const [cpu, setCpu] = useState<number>(35);
  const [interfaceStatus, setInterfaceStatus] = useState<'up' | 'down'>('up');
  const [seed, setSeed] = useState<number>(42);
  const [coupleMetrics, setCoupleMetrics] = useState<boolean>(true);
  const [activePreset, setActivePreset] = useState<string | null>(null);

  useEffect(() => {
    fetchFaultPresets()
      .then((data) => {
        if (data && data.presets) setPresets(data.presets);
      })
      .catch((err) => console.error('Failed to fetch presets:', err));
  }, []);

  const handleApplyPreset = (presetName: string) => {
    setActivePreset(presetName);
    if (presetName === 'congestion') {
      setSelectedTarget('HOSTEL_CORE_SW_01');
      setUtilization(96);
      setPacketLoss(8.5);
      setLatency(155);
      setQueueDrops(12500);
      setCrcErrors(0);
      setCpu(35);
      setInterfaceStatus('up');
    } else if (presetName === 'overload') {
      setSelectedTarget('DATA_CTR_CORE_01');
      setUtilization(40);
      setPacketLoss(0.5);
      setLatency(110);
      setQueueDrops(200);
      setCrcErrors(0);
      setCpu(98);
      setInterfaceStatus('up');
    } else if (presetName === 'interface_failure') {
      setSelectedTarget('HOSTEL_ACC_SW_01');
      setUtilization(0);
      setPacketLoss(100);
      setLatency(0);
      setQueueDrops(0);
      setCrcErrors(0);
      setCpu(20);
      setInterfaceStatus('down');
    } else if (presetName === 'crc_problem') {
      setSelectedTarget('LIB_ACC_SW_01');
      setUtilization(32);
      setPacketLoss(7.8);
      setLatency(25);
      setQueueDrops(0);
      setCrcErrors(92);
      setCpu(25);
      setInterfaceStatus('up');
    }
  };

  const handleExecuteInjection = async () => {
    const injections = [
      { target_device_id: selectedTarget, metric: 'link_utilization_pct', value: utilization },
      { target_device_id: selectedTarget, metric: 'packet_loss_pct', value: packetLoss },
      { target_device_id: selectedTarget, metric: 'latency_ms', value: latency },
      { target_device_id: selectedTarget, metric: 'queue_drops', value: queueDrops },
      { target_device_id: selectedTarget, metric: 'crc_errors', value: crcErrors },
      { target_device_id: selectedTarget, metric: 'cpu_utilization_pct', value: cpu },
      { target_device_id: selectedTarget, metric: 'interface_status', value: interfaceStatus },
    ];

    try {
      const rep = await injectAndDiagnose({
        base_scenario: '01_normal_network.json',
        injections,
        preset: activePreset || undefined,
        seed,
        couple_metrics: coupleMetrics,
      });
      onDiagnosisComplete(rep);
    } catch (err) {
      console.error('Failed to run chaos diagnosis:', err);
    }
  };

  const availableDevices = topology ? topology.nodes.map((n) => n.node_id) : [selectedTarget];

  return (
    <div className="noc-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Zap size={20} style={{ color: 'var(--status-amber)' }} />
          <div>
            <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, letterSpacing: '0.03em' }}>
              FAULT INJECTION STUDIO (CHAOS ENGINE)
            </h3>
            <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Break simulated network nodes in real-time to verify the multi-agent system diagnoses dynamically
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge badge-amber" style={{ fontSize: '0.7rem' }}>
            <ShieldAlert size={12} /> SIMULATED TELEMETRY
          </span>
        </div>
      </div>

      {/* Preset Buttons */}
      <div>
        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
          CHAOS PRESETS
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {['congestion', 'overload', 'interface_failure', 'crc_problem'].map((pName) => (
            <button
              key={pName}
              onClick={() => handleApplyPreset(pName)}
              style={{
                backgroundColor: activePreset === pName ? 'rgba(245, 158, 11, 0.2)' : '#111827',
                border: activePreset === pName ? '1px solid var(--status-amber)' : '1px solid var(--border-subtle)',
                color: activePreset === pName ? 'var(--status-amber)' : 'var(--text-primary)',
                borderRadius: '6px',
                padding: '6px 14px',
                fontSize: '0.775rem',
                fontWeight: 600,
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {pName.replace('_', ' ')}
            </button>
          ))}
          <button
            onClick={() => setActivePreset(null)}
            style={{
              backgroundColor: activePreset === null ? 'rgba(56, 189, 248, 0.2)' : '#111827',
              border: activePreset === null ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
              color: activePreset === null ? 'var(--accent-cyan)' : 'var(--text-muted)',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '0.775rem',
              cursor: 'pointer',
            }}
          >
            Custom
          </button>
        </div>
      </div>

      {/* Controls Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
        {/* Target Device */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
            TARGET TOPOLOGY NODE
          </label>
          <select
            value={selectedTarget}
            onChange={(e) => setSelectedTarget(e.target.value)}
            style={{
              backgroundColor: '#0a0f1d',
              border: '1px solid var(--border-subtle)',
              color: '#fff',
              borderRadius: '6px',
              padding: '8px 10px',
              fontSize: '0.8rem',
            }}
          >
            {availableDevices.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>

        {/* Link Utilization Slider */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>LINK UTILIZATION</span>
            <span className="font-mono" style={{ color: utilization >= 90 ? 'var(--status-red)' : 'var(--accent-cyan)' }}>
              {utilization}%
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={utilization}
            onChange={(e) => setUtilization(Number(e.target.value))}
            style={{ accentColor: utilization >= 90 ? 'var(--status-red)' : 'var(--accent-cyan)' }}
          />
        </div>

        {/* Packet Loss Slider */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>PACKET LOSS</span>
            <span className="font-mono" style={{ color: packetLoss >= 5 ? 'var(--status-red)' : 'var(--text-primary)' }}>
              {packetLoss}%
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            step="0.5"
            value={packetLoss}
            onChange={(e) => setPacketLoss(Number(e.target.value))}
            style={{ accentColor: 'var(--status-red)' }}
          />
        </div>

        {/* Latency Slider */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>ROUND-TRIP LATENCY</span>
            <span className="font-mono" style={{ color: latency >= 100 ? 'var(--status-amber)' : 'var(--text-primary)' }}>
              {latency} ms
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="500"
            value={latency}
            onChange={(e) => setLatency(Number(e.target.value))}
            style={{ accentColor: 'var(--status-amber)' }}
          />
        </div>

        {/* Queue Drops */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>EGRESS QUEUE DROPS</span>
            <span className="font-mono" style={{ color: queueDrops > 5000 ? 'var(--status-red)' : 'var(--text-primary)' }}>
              {queueDrops.toLocaleString()} pkts
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="30000"
            step="500"
            value={queueDrops}
            onChange={(e) => setQueueDrops(Number(e.target.value))}
            style={{ accentColor: 'var(--accent-blue)' }}
          />
        </div>

        {/* CRC Errors */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>CRC ERRORS</span>
            <span className="font-mono" style={{ color: crcErrors > 20 ? 'var(--status-amber)' : 'var(--text-primary)' }}>
              {crcErrors}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="250"
            value={crcErrors}
            onChange={(e) => setCrcErrors(Number(e.target.value))}
            style={{ accentColor: 'var(--status-amber)' }}
          />
        </div>

        {/* CPU Utilization */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>CONTROL PLANE CPU</span>
            <span className="font-mono" style={{ color: cpu >= 80 ? 'var(--status-red)' : 'var(--text-primary)' }}>
              {cpu}%
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={cpu}
            onChange={(e) => setCpu(Number(e.target.value))}
            style={{ accentColor: 'var(--accent-cyan)' }}
          />
        </div>

        {/* Interface Status Toggle & Seed */}
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
              INTERFACE STATE
            </label>
            <button
              onClick={() => setInterfaceStatus(interfaceStatus === 'up' ? 'down' : 'up')}
              style={{
                backgroundColor: interfaceStatus === 'up' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.2)',
                border: interfaceStatus === 'up' ? '1px solid var(--status-green)' : '1px solid var(--status-red)',
                color: interfaceStatus === 'up' ? 'var(--status-green)' : 'var(--status-red)',
                borderRadius: '6px',
                padding: '8px 12px',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              PORT {interfaceStatus.toUpperCase()}
            </button>
          </div>

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
              PRNG SEED
            </label>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
              style={{
                backgroundColor: '#0a0f1d',
                border: '1px solid var(--border-subtle)',
                color: '#fff',
                borderRadius: '6px',
                padding: '7px 10px',
                fontSize: '0.8rem',
              }}
            />
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '14px', flexWrap: 'wrap', gap: '12px' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={coupleMetrics}
            onChange={(e) => setCoupleMetrics(e.target.checked)}
          />
          Couple dependent metrics realistically (e.g. utilization induces queuing & latency)
        </label>

        <button
          onClick={handleExecuteInjection}
          disabled={isLoading}
          style={{
            backgroundColor: 'var(--status-amber)',
            color: '#05080f',
            border: 'none',
            borderRadius: '6px',
            padding: '8px 20px',
            fontSize: '0.85rem',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer',
          }}
        >
          <Play size={16} /> {isLoading ? 'Injecting & Diagnosing...' : 'Inject Fault & Diagnose Live'}
        </button>
      </div>
    </div>
  );
};
