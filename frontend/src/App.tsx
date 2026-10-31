import React, { useState, useEffect } from 'react';
import { HeaderBar } from './components/HeaderBar';
import { TopologyMap } from './components/TopologyMap';
import { AgentWire } from './components/AgentWire';
import { HypothesisRace } from './components/HypothesisRace';
import { MissingAgentToggle } from './components/MissingAgentToggle';
import { EvidenceBoard } from './components/EvidenceBoard';
import { RemediationPanel } from './components/RemediationPanel';
import { ReportViewer } from './components/ReportViewer';
import { PresentationModal } from './components/PresentationModal';
import { AblationPanel } from './components/AblationPanel';
import { ChaosPanel } from './components/ChaosPanel';
import { ReliabilityPanel } from './components/ReliabilityPanel';
import {
  fetchTopology,
  fetchScenarios,
  runScenario,
  fetchMessages,
  fetchMarkdownReport,
} from './services/api';
import { CampusTopology, ScenarioItem, FinalDiagnosisReport, AgentMessage } from './types';
import { AlertTriangle, Network, Cpu, Radio, FileText, CheckCircle2, GitCompare, Zap, Target } from 'lucide-react';

export const App: React.FC = () => {
  const [topology, setTopology] = useState<CampusTopology | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>('07_hackathon_demo.json');
  const [report, setReport] = useState<FinalDiagnosisReport | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [markdownReport, setMarkdownReport] = useState<string>('');
  const [disabledAgents, setDisabledAgents] = useState<string[]>([]);
  const [hoveredDeviceId, setHoveredDeviceId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isDemoModeOpen, setIsDemoModeOpen] = useState<boolean>(false);
  const [activeMainTab, setActiveMainTab] = useState<'cockpit' | 'wire' | 'report' | 'ablation' | 'chaos' | 'reliability'>('cockpit');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Initial Load
  useEffect(() => {
    async function init() {
      try {
        const [topo, scens] = await Promise.all([fetchTopology(), fetchScenarios()]);
        setTopology(topo);
        setScenarios(scens);
        // Execute initial flagship scenario
        executeDiagnosis('07_hackathon_demo.json', []);
      } catch (err: any) {
        console.error('Initialization error:', err);
        setErrorMessage(
          'Backend unavailable. Start FastAPI backend on port 8000: (cd backend && source ../.venv/bin/activate && uvicorn app.main:app --reload)'
        );
      }
    }
    init();
  }, []);

  const executeDiagnosis = async (scenarioFile: string, disabled: string[]) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const rep = await runScenario(scenarioFile, disabled);
      setReport(rep);

      const sid = rep.extensions?.session_id || rep.incident_id;
      const [msgsData, mdText] = await Promise.all([
        fetchMessages(sid).catch(() => ({ session_id: sid, messages: [] })),
        fetchMarkdownReport(sid).catch(() => ''),
      ]);

      setMessages(msgsData.messages);
      setMarkdownReport(mdText);
    } catch (err: any) {
      console.error('Diagnosis failed:', err);
      setErrorMessage(
        err?.message || 'Backend connection error. Please verify FastAPI backend is running on port 8000.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectScenario = (scen: string) => {
    setSelectedScenario(scen);
    executeDiagnosis(scen, disabledAgents);
  };

  const handleToggleAgent = (agentName: string) => {
    const nextDisabled = disabledAgents.includes(agentName)
      ? disabledAgents.filter((a) => a !== agentName)
      : [...disabledAgents, agentName];
    setDisabledAgents(nextDisabled);
    executeDiagnosis(selectedScenario, nextDisabled);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-dark)' }}>
      {/* Top At-A-Glance Bar */}
      <HeaderBar
        report={report}
        scenarios={scenarios}
        selectedScenario={selectedScenario}
        onSelectScenario={handleSelectScenario}
        onRunDiagnosis={() => executeDiagnosis(selectedScenario, disabledAgents)}
        isLoading={isLoading}
        onOpenDemoMode={() => setIsDemoModeOpen(true)}
      />

      {/* Backend Error Alert Banner */}
      {errorMessage && (
        <div
          style={{
            margin: '16px 24px 0 24px',
            padding: '12px 16px',
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid var(--status-red)',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            color: '#fca5a5',
            fontSize: '0.85rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <AlertTriangle size={18} style={{ color: 'var(--status-red)' }} />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => executeDiagnosis(selectedScenario, disabledAgents)}
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.3)',
              border: '1px solid var(--status-red)',
              color: '#fff',
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '0.75rem',
              cursor: 'pointer',
            }}
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Main Container */}
      <main style={{ padding: '20px 24px', flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Navigation Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={() => setActiveMainTab('cockpit')}
              style={{
                backgroundColor: activeMainTab === 'cockpit' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                color: activeMainTab === 'cockpit' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                border: activeMainTab === 'cockpit' ? '1px solid var(--accent-cyan)' : '1px solid transparent',
                borderRadius: '6px',
                padding: '6px 16px',
                fontSize: '0.825rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer',
              }}
            >
              <Network size={16} /> Cockpit & Topology
            </button>

            <button
              onClick={() => setActiveMainTab('wire')}
              style={{
                backgroundColor: activeMainTab === 'wire' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                color: activeMainTab === 'wire' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                border: activeMainTab === 'wire' ? '1px solid var(--accent-cyan)' : '1px solid transparent',
                borderRadius: '6px',
                padding: '6px 16px',
                fontSize: '0.825rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer',
              }}
            >
              <Radio size={16} /> Agent Wire ({messages.length})
            </button>

            <button
              onClick={() => setActiveMainTab('report')}
              style={{
                backgroundColor: activeMainTab === 'report' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                color: activeMainTab === 'report' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                border: activeMainTab === 'report' ? '1px solid var(--accent-cyan)' : '1px solid transparent',
                borderRadius: '6px',
                padding: '6px 16px',
                fontSize: '0.825rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer',
              }}
            >
              <FileText size={16} /> Section 6 Report
            </button>

            <button
              onClick={() => setActiveMainTab('ablation')}
              style={{
                backgroundColor: activeMainTab === 'ablation' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                color: activeMainTab === 'ablation' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                border: activeMainTab === 'ablation' ? '1px solid var(--accent-cyan)' : '1px solid transparent',
                borderRadius: '6px',
                padding: '6px 16px',
                fontSize: '0.825rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer',
              }}
            >
              <GitCompare size={16} /> Collaboration Proof
            </button>

            <button
              onClick={() => setActiveMainTab('chaos')}
              style={{
                backgroundColor: activeMainTab === 'chaos' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                color: activeMainTab === 'chaos' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                border: activeMainTab === 'chaos' ? '1px solid var(--accent-cyan)' : '1px solid transparent',
                borderRadius: '6px',
                padding: '6px 16px',
                fontSize: '0.825rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer',
              }}
            >
              <Zap size={16} /> Chaos Studio
            </button>

            <button
              onClick={() => setActiveMainTab('reliability')}
              style={{
                backgroundColor: activeMainTab === 'reliability' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                color: activeMainTab === 'reliability' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                border: activeMainTab === 'reliability' ? '1px solid var(--accent-cyan)' : '1px solid transparent',
                borderRadius: '6px',
                padding: '6px 16px',
                fontSize: '0.825rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer',
              }}
            >
              <Target size={16} /> Reliability & ECE
            </button>
          </div>

          {report?.suspected_root_cause && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Consensus Verdict:</span>
              <strong style={{ color: 'var(--accent-cyan)' }}>{report.suspected_root_cause}</strong>
            </div>
          )}
        </div>

        {/* Missing Agent Toggle ("What if an agent were missing?") */}
        <MissingAgentToggle
          disabledAgents={disabledAgents}
          onToggleAgent={handleToggleAgent}
          isLoading={isLoading}
        />

        {/* Tab 1: Cockpit View (Topology + Race + Evidence + Remediation) */}
        {activeMainTab === 'cockpit' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '20px' }}>
            {/* Left 7 Columns: Topology Map */}
            <div style={{ gridColumn: 'span 7' }}>
              <TopologyMap
                topology={topology}
                report={report}
                hoveredDeviceId={hoveredDeviceId}
                onSelectDevice={(dev) => setHoveredDeviceId(dev)}
              />
            </div>

            {/* Right 5 Columns: Hypothesis Race */}
            <div style={{ gridColumn: 'span 5', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <HypothesisRace
                hypotheses={report?.extensions?.hypotheses_ranking || []}
                status={report?.status || 'diagnosed'}
              />
              <RemediationPanel remediation={report?.extensions?.simulated_remediation} />
            </div>

            {/* Full Width Bottom: Evidence Board */}
            <div style={{ gridColumn: 'span 12' }}>
              <EvidenceBoard
                evidence={report?.supporting_evidence || []}
                sources={report?.evidence_sources || []}
                onHoverDevice={(dev) => setHoveredDeviceId(dev)}
              />
            </div>
          </div>
        )}

        {/* Tab 2: Agent Wire View (Chronological protocol messages) */}
        {activeMainTab === 'wire' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '20px' }}>
            <div style={{ gridColumn: 'span 12' }}>
              <AgentWire messages={messages} />
            </div>
          </div>
        )}

        {/* Tab 3: Strict Report View */}
        {activeMainTab === 'report' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '20px' }}>
            <div style={{ gridColumn: 'span 12' }}>
              <ReportViewer report={report} markdownText={markdownReport} />
            </div>
          </div>
        )}

        {/* Tab 4: Collaboration Proof (Agent Ablation) */}
        {activeMainTab === 'ablation' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '20px' }}>
            <div style={{ gridColumn: 'span 12' }}>
              <AblationPanel
                sessionId={report?.extensions?.session_id || report?.incident_id}
                onSelectDisabledAgent={(agentName) => {
                  handleToggleAgent(agentName);
                  setActiveMainTab('cockpit');
                }}
              />
            </div>
          </div>
        )}

        {/* Tab 5: Chaos Studio (Fault Injection) */}
        {activeMainTab === 'chaos' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '20px' }}>
            <div style={{ gridColumn: 'span 12' }}>
              <ChaosPanel
                topology={topology}
                onDiagnosisComplete={(rep) => {
                  setReport(rep);
                  const sid = rep.extensions?.session_id || rep.incident_id;
                  if (sid) {
                    fetchMessages(sid).then((res) => setMessages(res.messages)).catch(console.error);
                    fetchMarkdownReport(sid).then(setMarkdownReport).catch(console.error);
                  }
                }}
                isLoading={isLoading}
              />
            </div>
          </div>
        )}

        {/* Tab 6: Reliability & Calibration */}
        {activeMainTab === 'reliability' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '20px' }}>
            <div style={{ gridColumn: 'span 12' }}>
              <ReliabilityPanel />
            </div>
          </div>
        )}
      </main>

      {/* Presenter Mode Modal */}
      <PresentationModal isOpen={isDemoModeOpen} onClose={() => setIsDemoModeOpen(false)} />
    </div>
  );
};

export default App;
