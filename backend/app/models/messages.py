from enum import Enum
from typing import Optional, List, Dict, Any, Union, Set, ClassVar
from pydantic import BaseModel, Field, field_validator


class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    PERFORMANCE_AGENT = "performance_agent"
    INFRASTRUCTURE_AGENT = "infrastructure_agent"
    CONNECTIVITY_AGENT = "connectivity_agent"
    CORRELATION_AGENT = "correlation_agent"
    REPORTING_AGENT = "reporting_agent"
    BROADCAST = "broadcast"


class MessageType(str, Enum):
    TASK_DISPATCH = "task_dispatch"
    DIAGNOSTIC_FINDING = "diagnostic_finding"
    FINDINGS_BUNDLE = "findings_bundle"
    CLARIFICATION_REQUEST = "clarification_request"
    CLARIFICATION_RESPONSE = "clarification_response"
    CONSOLIDATED_DIAGNOSIS = "consolidated_diagnosis"
    FINAL_REPORT = "final_report"
    AGENT_ERROR = "agent_error"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceItem(BaseModel):
    metric: str
    value: Union[float, int, str, bool, None]
    interpretation: str
    baseline: Optional[Union[float, int, str, None]] = None
    device_id: Optional[str] = None


class AgentMessage(BaseModel):
    message_id: str = Field(..., description="Unique message UUID")
    session_id: str = Field(..., description="Diagnostic session ID, format DX-YYYY-NNNN")
    timestamp: str = Field(..., description="ISO-8601 timestamp")
    source_agent: AgentRole = Field(..., description="Sender agent identity")
    target_agent: AgentRole = Field(..., description="Recipient agent identity")
    message_type: MessageType = Field(..., description="Type of message according to agent protocol")
    schema_version: str = Field("1.0", description="Protocol version, must be '1.0'")
    
    device_ids: List[str] = Field(default_factory=list, description="IDs of devices referenced in this message")
    metric: Optional[str] = Field(default="", description="Primary metric evaluated, if applicable")
    value: Optional[Union[float, int, str, bool, Dict[str, Any], List[Any]]] = Field(
        default=None, description="Primary metric value or summary data"
    )
    unit: Optional[str] = Field(default="", description="Unit of measurement (e.g. %, ms, drops, errors)")
    severity: SeverityLevel = Field(SeverityLevel.LOW, description="Severity assessment")
    finding: str = Field(..., description="Clear human-readable summary of the agent's finding")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Array of concrete supporting evidence items")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Agent confidence score [0.0 - 1.0]")
    possible_causes: List[str] = Field(default_factory=list, description="Candidate causes identified by this agent")
    recommended_checks: List[str] = Field(default_factory=list, description="Immediate verification checks proposed")
    in_reply_to: Optional[str] = Field(None, description="Message ID this message responds to (for request/response)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary supplemental diagnostic context")

    ALLOWED_UNITS: ClassVar[Set[str]] = {
        "%", "ms", "drops", "errors", "devices", "ratio", "events",
        "bytes", "mbps", "gbps", "packets", "pkts", "s", "sec", ""
    }

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if v != "1.0":
            raise ValueError(f"Unsupported schema_version: '{v}'. Only '1.0' is supported.")
        return v

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: Optional[str]) -> str:
        if v is None:
            return ""
        v_clean = v.strip().lower()
        if v_clean and v_clean not in cls.ALLOWED_UNITS:
            raise ValueError(
                f"Invalid or unsupported unit '{v}'. Allowed network diagnostic units are: "
                f"{sorted(list(cls.ALLOWED_UNITS))}"
            )
        return v

