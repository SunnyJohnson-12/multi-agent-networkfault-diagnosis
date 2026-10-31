import asyncio
import uuid
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from app.models.telemetry import DeviceTelemetry
from app.models.topology import CampusTopology
from app.models.messages import AgentRole, MessageType, SeverityLevel, AgentMessage
from app.models.diagnosis import FinalDiagnosisReport
from app.orchestration.message_bus import MessageBus
from app.agents.performance_agent import PerformanceAgent
from app.agents.infrastructure_agent import InfrastructureAgent
from app.agents.connectivity_agent import ConnectivityAgent
from app.agents.correlation_agent import CorrelationAgent
from app.agents.reporting_agent import ReportingAgent
from app.services.session_store import session_store, SessionRecord
from app.validation.validators import validate_telemetry_item, validate_topology, ValidationErrorResponse


class Orchestrator:
    """Central diagnostic orchestrator coordinating session lifecycle, async agent dispatch,

    degradation handling, cross-query routing, and report generation.
    """

    def __init__(self, agent_timeout_seconds: float = 3.0):
        self.agent_timeout_seconds = agent_timeout_seconds
        self.performance_agent = PerformanceAgent()
        self.infrastructure_agent = InfrastructureAgent()
        self.connectivity_agent = ConnectivityAgent()
        self.correlation_agent = CorrelationAgent()
        self.reporting_agent = ReportingAgent()

    async def run_diagnostic_session(
        self,
        telemetry_raw: List[Dict[str, Any]],
        topology_raw: Optional[Dict[str, Any]] = None,
        incident_id: Optional[str] = None,
        disabled_agents: Optional[List[str]] = None,
    ) -> SessionRecord:
        """Execute a full multi-agent diagnostic session."""
        disabled_agents_set: Set[str] = set(disabled_agents or [])
        session_id = session_store.generate_session_id()
        if not incident_id:
            incident_id = f"INC-{uuid.uuid4().hex[:4].upper()}"

        # 1. Input Validation
        validated_telemetry: List[DeviceTelemetry] = []
        for idx, item in enumerate(telemetry_raw):
            try:
                validated_telemetry.append(validate_telemetry_item(item, require_mandatory=False))
            except ValidationErrorResponse:
                raise
            except Exception as e:
                raise ValidationErrorResponse(
                    error_code="INVALID_TELEMETRY",
                    message=f"Telemetry error at index {idx}: {str(e)}",
                )

        validated_topology: Optional[CampusTopology] = None
        if topology_raw:
            validated_topology = validate_topology(topology_raw)

        # 2. Initialize Session Message Bus
        bus = MessageBus(session_id=session_id)

        # 3. Publish initial Task Dispatch from Orchestrator
        dispatch_msg = AgentMessage(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            source_agent=AgentRole.ORCHESTRATOR,
            target_agent=AgentRole.BROADCAST,
            message_type=MessageType.TASK_DISPATCH,
            schema_version="1.0",
            device_ids=[t.device_id for t in validated_telemetry],
            finding=f"Initiating multi-agent network fault investigation for incident {incident_id}.",
            severity=SeverityLevel.LOW,
            metadata={"incident_id": incident_id, "disabled_agents": list(disabled_agents_set)},
        )
        await bus.publish(dispatch_msg)

        # 4. Dispatch tasks in parallel to domain agents with timeouts
        findings: List[AgentMessage] = []
        degraded_agents: List[str] = []

        async def run_agent(agent_name: str, coro_fn) -> Optional[AgentMessage]:
            if agent_name in disabled_agents_set:
                degraded_agents.append(agent_name)
                err_msg = AgentMessage(
                    message_id=str(uuid.uuid4()),
                    session_id=session_id,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    source_agent=AgentRole(agent_name),
                    target_agent=AgentRole.ORCHESTRATOR,
                    message_type=MessageType.AGENT_ERROR,
                    schema_version="1.0",
                    finding=f"Agent '{agent_name}' disabled by user or degraded.",
                    severity=SeverityLevel.HIGH,
                )
                await bus.publish(err_msg)
                return None

            try:
                msg = await asyncio.wait_for(coro_fn(), timeout=self.agent_timeout_seconds)
                await bus.publish(msg)
                return msg
            except asyncio.TimeoutError:
                degraded_agents.append(agent_name)
                timeout_msg = AgentMessage(
                    message_id=str(uuid.uuid4()),
                    session_id=session_id,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    source_agent=AgentRole(agent_name),
                    target_agent=AgentRole.ORCHESTRATOR,
                    message_type=MessageType.AGENT_ERROR,
                    schema_version="1.0",
                    finding=f"Agent '{agent_name}' timed out after {self.agent_timeout_seconds}s.",
                    severity=SeverityLevel.HIGH,
                )
                await bus.publish(timeout_msg)
                return None
            except Exception as e:
                degraded_agents.append(agent_name)
                fail_msg = AgentMessage(
                    message_id=str(uuid.uuid4()),
                    session_id=session_id,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    source_agent=AgentRole(agent_name),
                    target_agent=AgentRole.ORCHESTRATOR,
                    message_type=MessageType.AGENT_ERROR,
                    schema_version="1.0",
                    finding=f"Agent '{agent_name}' encountered runtime failure: {str(e)}",
                    severity=SeverityLevel.HIGH,
                )
                await bus.publish(fail_msg)
                return None

        # Execute parallel domain agent collection
        tasks = [
            run_agent("performance_agent", lambda: self.performance_agent.analyze(session_id, validated_telemetry, validated_topology)),
            run_agent("infrastructure_agent", lambda: self.infrastructure_agent.analyze(session_id, validated_telemetry, validated_topology)),
            run_agent("connectivity_agent", lambda: self.connectivity_agent.analyze(session_id, validated_telemetry, validated_topology)),
        ]
        results = await asyncio.gather(*tasks)
        for res in results:
            if res is not None:
                findings.append(res)

        # 5. Bundle findings and route to Correlation Agent
        bundle_msg = AgentMessage(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            source_agent=AgentRole.ORCHESTRATOR,
            target_agent=AgentRole.CORRELATION_AGENT,
            message_type=MessageType.FINDINGS_BUNDLE,
            schema_version="1.0",
            finding=f"Dispatching bundle of {len(findings)} agent findings for correlation.",
            severity=SeverityLevel.LOW,
            metadata={"findings_count": len(findings), "degraded_agents": degraded_agents},
        )
        await bus.publish(bundle_msg)

        # 6. Execute Correlation with dynamic Cross-Query Collaboration
        conn_handler = None
        if "connectivity_agent" not in disabled_agents_set:
            conn_handler = self.connectivity_agent.handle_clarification_request

        consolidated_msg, clarif_req, clarif_resp = await self.correlation_agent.correlate(
            session_id=session_id,
            findings=findings,
            telemetry=validated_telemetry,
            topology=validated_topology,
            connectivity_agent_handler=conn_handler,
            degraded_agents=degraded_agents,
        )

        # If a cross-query occurred, log both messages onto the bus!
        if clarif_req:
            await bus.publish(clarif_req)
        if clarif_resp:
            await bus.publish(clarif_resp)

        await bus.publish(consolidated_msg)

        # 7. Execute Reporting Agent
        final_msg, final_report, markdown_report = await self.reporting_agent.generate_report(
            session_id=session_id,
            incident_id=incident_id,
            diagnosis_msg=consolidated_msg,
            raw_messages=bus.get_messages(),
            telemetry=validated_telemetry,
        )
        await bus.publish(final_msg)

        # 8. Persist Session Record
        session_record = session_store.save_session(
            session_id=session_id,
            incident_id=incident_id,
            telemetry_raw=telemetry_raw,
            topology_raw=topology_raw,
            final_report=final_report,
            messages=[m.model_dump() for m in bus.get_messages()],
            markdown_report=markdown_report,
        )

        return session_record


# Global singleton orchestrator
orchestrator = Orchestrator()
