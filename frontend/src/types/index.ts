export interface TopologyNode {
  node_id: string;
  name: string;
  node_type: string;
  segment: string;
  ip_address?: string;
  status: string;
  model?: string;
  x?: number;
  y?: number;
}

export interface TopologyLink {
  link_id: string;
  source_node: string;
  target_node: string;
  source_interface: string;
  target_interface: string;
  bandwidth_mbps: number;
  is_uplink: boolean;
  status: string;
  utilization_pct?: number;
}

export interface CampusTopology {
  topology_id: string;
  name: string;
  nodes: TopologyNode[];
  links: TopologyLink[];
}

export interface EvidenceItem {
  metric: string;
  value: any;
  interpretation: string;
  baseline?: any;
  device_id?: string;
}

export interface AgentMessage {
  message_id: string;
  session_id: string;
  timestamp: string;
  source_agent: string;
  target_agent: string;
  message_type: string;
  schema_version: string;
  device_ids: string[];
  metric?: string;
  value?: any;
  unit?: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  finding: string;
  evidence: EvidenceItem[];
  confidence: number;
  possible_causes: string[];
  recommended_checks: string[];
  in_reply_to?: string;
  metadata?: Record<string, any>;
}

export interface SupportingEvidenceItem {
  metric: string;
  value: any;
  interpretation: string;
}

export interface HypothesisScore {
  hypothesis: string;
  score: number;
  matched_signals: string[];
  contradictory_signals: string[];
  explanation: string;
}

export interface SimulatedRemediation {
  action_type: string;
  description: string;
  pre_remediation_metric: string;
  pre_remediation_value: any;
  post_remediation_metric: string;
  post_remediation_value: any;
  estimated_impact: string;
  disclaimer: string;
}

export interface DiagnosticExtensions {
  session_id?: string;
  severity?: string;
  scope?: string;
  hypotheses_ranking: HypothesisScore[];
  agent_message_count: number;
  timeline: Array<{
    step: number;
    timestamp: string;
    source: string;
    target: string;
    type: string;
    finding_snippet: string;
  }>;
  simulated_remediation?: SimulatedRemediation;
  cross_query_conducted: boolean;
  degraded_agents: string[];
  claim_ledger?: ClaimLedger;
  traceability?: TraceabilityCoverage;
  ablation?: AblationReport;
}

export interface FinalDiagnosisReport {
  incident_id: string;
  status: 'diagnosed' | 'ambiguous' | 'no_fault_detected' | 'insufficient_data' | 'error';
  suspected_root_cause: string;
  confidence: number;
  affected_devices: string[];
  supporting_evidence: SupportingEvidenceItem[];
  alternative_causes: string[];
  recommended_actions: string[];
  evidence_sources: string[];
  limitations: string[];
  extensions?: DiagnosticExtensions;
}

export interface ScenarioItem {
  file: string;
  scenario_id: string;
  name: string;
  description: string;
  expected_fault: string;
  incident_id: string;
  disabled_agents: string[];
  telemetry_count: number;
}

export interface ClaimSource {
  message_id: string;
  source_agent: string;
  metric: string;
  value: any;
  unit?: string;
  device_id?: string;
}

export interface ReportClaim {
  claim_id: string;
  statement: string;
  claim_type: string;
  sources: ClaimSource[];
  confidence: number;
  footnote_tag: string;
}

export interface ClaimLedger {
  claims: ReportClaim[];
  unsupported_claims: Array<{ statement: string; reason: string }>;
  total_claims: number;
  supported_claims: number;
  coverage_percentage: number;
}

export interface TraceabilityCoverage {
  total_claims: number;
  supported_claims: number;
  coverage_pct: number;
  is_fully_traceable: boolean;
}

export interface AgentAblationResult {
  agent_name: string;
  confidence: number;
  confidence_delta: number;
  status: string;
  status_degraded: boolean;
  suspected_root_cause: string;
  root_cause_changed: boolean;
  top_hypothesis: string;
  runner_up_hypothesis?: string;
  margin: number;
  evidence_sources: string[];
  lost_evidence: string[];
  added_limitations: string[];
  verdict: string;
  impact_score: number;
}

export interface AblationReport {
  session_id: string;
  incident_id: string;
  baseline_confidence: number;
  baseline_status: string;
  baseline_root_cause: string;
  configurations: Array<{
    config: string;
    disabled: string[];
    confidence: number;
    status: string;
    root_cause: string;
    margin: number;
  }>;
  agent_contributions: AgentAblationResult[];
  most_critical_agent: string;
  collaboration_proven: boolean;
  summary: string;
}

export interface ReliabilityBin {
  bin_index: number;
  bin_range: string;
  bin_lower: number;
  bin_upper: number;
  mean_confidence: number;
  empirical_accuracy: number;
  sample_count: number;
}

export interface CalibrationReport {
  total_runs: number;
  overall_accuracy: number;
  expected_calibration_error: number;
  mean_confidence_correct: number;
  mean_confidence_incorrect: number;
  ambiguous_rate: number;
  abstain_rate: number;
  per_class_accuracy: Record<string, number>;
  confusion_matrix: Record<string, Record<string, number>>;
  reliability_diagram: ReliabilityBin[];
  headline: string;
  calibrated_at: string;
}

export interface FaultPreset {
  name: string;
  description: string;
  target_device: string;
  injections: Array<{
    metric: string;
    value: any;
  }>;
}
