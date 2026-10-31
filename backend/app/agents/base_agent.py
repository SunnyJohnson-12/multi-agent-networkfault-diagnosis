import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from app.models.messages import AgentMessage, AgentRole, MessageType, SeverityLevel, EvidenceItem


class BaseAgent:
    """Base class for all specialized diagnostic agents enforcing protocol compliance."""

    def __init__(self, role: AgentRole):
        self.role = role

    def create_message(
        self,
        session_id: str,
        target_agent: AgentRole,
        message_type: MessageType,
        finding: str,
        severity: SeverityLevel = SeverityLevel.LOW,
        device_ids: Optional[List[str]] = None,
        metric: Optional[str] = "",
        value: Optional[Union[float, int, str, bool, Dict[str, Any], List[Any]]] = None,
        unit: Optional[str] = "",
        evidence: Optional[List[EvidenceItem]] = None,
        confidence: float = 0.0,
        possible_causes: Optional[List[str]] = None,
        recommended_checks: Optional[List[str]] = None,
        in_reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        return AgentMessage(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            source_agent=self.role,
            target_agent=target_agent,
            message_type=message_type,
            schema_version="1.0",
            device_ids=device_ids or [],
            metric=metric or "",
            value=value,
            unit=unit or "",
            severity=severity,
            finding=finding,
            evidence=evidence or [],
            confidence=max(0.0, min(1.0, confidence)),
            possible_causes=possible_causes or [],
            recommended_checks=recommended_checks or [],
            in_reply_to=in_reply_to,
            metadata=metadata or {},
        )
