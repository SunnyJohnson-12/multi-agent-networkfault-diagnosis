import { CampusTopology, FinalDiagnosisReport, ScenarioItem, AgentMessage } from '../types';

const API_BASE = '/api';

export async function fetchHealth(): Promise<any> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Failed to fetch system health');
  return res.json();
}

export async function fetchTopology(): Promise<CampusTopology> {
  const res = await fetch(`${API_BASE}/topology`);
  if (!res.ok) throw new Error('Failed to fetch campus topology');
  return res.json();
}

export async function fetchScenarios(): Promise<ScenarioItem[]> {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) throw new Error('Failed to fetch scenarios');
  return res.json();
}

export async function runScenario(
  name: string,
  disabledAgents: string[] = []
): Promise<FinalDiagnosisReport> {
  const res = await fetch(`${API_BASE}/scenarios/${encodeURIComponent(name)}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ disabled_agents: disabledAgents }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || 'Failed to run scenario');
  }
  return res.json();
}

export async function fetchMessages(sessionOrIncidentId: string): Promise<{ session_id: string; messages: AgentMessage[] }> {
  const res = await fetch(`${API_BASE}/diagnosis/${encodeURIComponent(sessionOrIncidentId)}/messages`);
  if (!res.ok) throw new Error('Failed to fetch session messages');
  return res.json();
}

export async function fetchMarkdownReport(sessionOrIncidentId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/diagnosis/${encodeURIComponent(sessionOrIncidentId)}/report.md`);
  if (!res.ok) throw new Error('Failed to fetch markdown report');
  return res.text();
}

export async function fetchAblation(sessionOrIncidentId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/diagnosis/${encodeURIComponent(sessionOrIncidentId)}/ablation`);
  if (!res.ok) throw new Error('Failed to fetch ablation analysis');
  return res.json();
}

export async function fetchFaultPresets(): Promise<any> {
  const res = await fetch(`${API_BASE}/inject/presets`);
  if (!res.ok) throw new Error('Failed to fetch fault injection presets');
  return res.json();
}

export async function injectAndDiagnose(params: {
  base_scenario?: string;
  injections?: Array<{ target_device_id: string; metric: string; value: any }>;
  preset?: string;
  seed?: number;
  couple_metrics?: boolean;
}): Promise<FinalDiagnosisReport> {
  const res = await fetch(`${API_BASE}/inject/diagnose`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || 'Failed to inject fault and diagnose');
  }
  return res.json();
}

export async function fetchCalibration(): Promise<any> {
  const res = await fetch(`${API_BASE}/calibration`);
  if (!res.ok) throw new Error('Failed to fetch calibration report');
  return res.json();
}

export async function fetchClaims(sessionOrIncidentId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/diagnosis/${encodeURIComponent(sessionOrIncidentId)}/claims`);
  if (!res.ok) throw new Error('Failed to fetch claims ledger');
  return res.json();
}

