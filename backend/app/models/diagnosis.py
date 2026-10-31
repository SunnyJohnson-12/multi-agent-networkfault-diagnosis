from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator


class DiagnosisStatus(str, Enum):
    DIAGNOSED = "diagnosed"
    AMBIGUOUS = "ambiguous"
    NO_FAULT_DETECTED = "no_fault_detected"
    INSUFFICIENT_DATA = "insufficient_data"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    ERROR = "error"


class SupportingEvidenceItem(BaseModel):
    metric: str
    value: Union[float, int, str, bool]
    interpretation: str


class HypothesisScore(BaseModel):
    hypothesis: str
    score: float = Field(..., ge=0.0, le=1.0)
    matched_signals: List[str] = Field(default_factory=list)
    contradictory_signals: List[str] = Field(default_factory=list)
    explanation: str


class SimulatedRemediation(BaseModel):
    action_type: str
    description: str
    pre_remediation_metric: str
    pre_remediation_value: Union[float, int, str]
    post_remediation_metric: str
    post_remediation_value: Union[float, int, str]
    estimated_impact: str
    disclaimer: str = "SIMULATION ONLY — human review required. Does not modify physical infrastructure."


class DiagnosticExtensions(BaseModel):
    session_id: Optional[str] = None
    severity: Optional[str] = None
    timestamp: Optional[str] = None
    scope: Optional[str] = None
    hypotheses_ranking: List[HypothesisScore] = Field(default_factory=list)
    agent_message_count: int = 0
    agent_findings: List[Dict[str, Any]] = Field(default_factory=list, description="Structured agent findings summary")
    message_ids: List[str] = Field(default_factory=list, description="List of protocol message UUIDs in this session")
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    simulated_remediation: Optional[SimulatedRemediation] = None
    cross_query_conducted: bool = False
    degraded_agents: List[str] = Field(default_factory=list)
    claim_ledger: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Claim ledger mapping factual statements to message sources")
    traceability: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Traceability provenance metrics")
    ablation: Optional[Dict[str, Any]] = Field(default=None, description="Multi-agent ablation configuration report")


class FinalDiagnosisReport(BaseModel):
    incident_id: str = Field(..., description="Unique incident identifier, e.g. INC-8832")
    status: DiagnosisStatus = Field(..., description="Diagnostic outcome status")
    suspected_root_cause: str = Field(..., description="Evidence-backed primary root cause")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence level [0.0 - 1.0]")
    affected_devices: List[str] = Field(..., description="List of confirmed impacted device IDs")
    supporting_evidence: List[SupportingEvidenceItem] = Field(..., description="Concrete telemetry evidence items")
    alternative_causes: List[str] = Field(..., description="Ranked alternative possibilities")
    recommended_actions: List[str] = Field(..., description="Prioritized recommendations with human review phrasing")
    evidence_sources: List[str] = Field(..., description="Contributing agent identifiers")
    limitations: List[str] = Field(..., description="Known uncertainties, blind spots, or missing telemetry")
    extensions: Optional[DiagnosticExtensions] = None

    @field_validator("recommended_actions")
    @classmethod
    def validate_recommended_actions(cls, actions: List[str]) -> List[str]:
        validated = []
        for action in actions:
            if not action.endswith("Recommended action — human review required."):
                if action.endswith("."):
                    action = f"{action[:-1]} — Recommended action — human review required."
                else:
                    action = f"{action} — Recommended action — human review required."
            validated.append(action)
        return validated

    def to_section6_dict(self, include_extensions: bool = True) -> Dict[str, Any]:
        """Convert to Section 6 exact JSON schema dictionary representation."""
        base = {
            "incident_id": self.incident_id,
            "status": self.status.value,
            "suspected_root_cause": self.suspected_root_cause,
            "confidence": round(float(self.confidence), 2),
            "affected_devices": self.affected_devices,
            "supporting_evidence": [
                {"metric": e.metric, "value": e.value, "interpretation": e.interpretation}
                for e in self.supporting_evidence
            ],
            "alternative_causes": self.alternative_causes,
            "recommended_actions": self.recommended_actions,
            "evidence_sources": self.evidence_sources,
            "limitations": self.limitations,
        }
        if include_extensions:
            if self.extensions:
                ext_dict = self.extensions.model_dump()
                base["extensions"] = ext_dict
                base["severity"] = self.extensions.severity or "medium"
                base["timestamp"] = self.extensions.timestamp or ""
                base["agent_findings"] = self.extensions.agent_findings or []
                base["message_ids"] = self.extensions.message_ids or []
            else:
                base["severity"] = "medium"
                base["timestamp"] = ""
                base["agent_findings"] = []
                base["message_ids"] = []
        return base
