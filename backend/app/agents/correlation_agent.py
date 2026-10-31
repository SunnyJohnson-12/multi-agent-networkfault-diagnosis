from typing import List, Optional, Dict, Any, Set, Tuple
from app.agents.base_agent import BaseAgent
from app.models.messages import AgentRole, MessageType, SeverityLevel, EvidenceItem, AgentMessage
from app.models.telemetry import DeviceTelemetry
from app.models.topology import CampusTopology
from app.models.diagnosis import DiagnosisStatus
from app.services.hypothesis_scoring import HypothesisScoringEngine
from app.services.llm_client import LLMClient


class CorrelationAgent(BaseAgent):
    """Specialized agent consuming all findings, initiating cross-query inquiries,

    scoring competing hypotheses, and producing the consolidated diagnosis.
    """

    def __init__(self):
        super().__init__(AgentRole.CORRELATION_AGENT)
        self.llm_client = LLMClient()

    async def correlate(
        self,
        session_id: str,
        findings: List[AgentMessage],
        telemetry: List[DeviceTelemetry],
        topology: Optional[CampusTopology] = None,
        connectivity_agent_handler: Optional[Any] = None,
        degraded_agents: Optional[List[str]] = None,
    ) -> Tuple[AgentMessage, Optional[AgentMessage], Optional[AgentMessage]]:
        """Correlate findings bundle, perform cross-query clarification, and emit consolidated diagnosis."""
        degraded_agents = degraded_agents or []

        # 1. Gather all affected devices and supporting evidence items across all agents
        all_affected: Set[str] = set()
        all_evidence: List[EvidenceItem] = []
        contributing_agents: Set[str] = set()
        known_numbers: Set[float] = set()

        for f in findings:
            contributing_agents.add(f.source_agent.value)
            all_affected.update(f.device_ids)
            all_evidence.extend(f.evidence)
            if isinstance(f.value, (int, float)):
                known_numbers.add(float(f.value))
            for ev in f.evidence:
                if isinstance(ev.value, (int, float)):
                    known_numbers.add(float(ev.value))

        for t in telemetry:
            for val in (t.link_utilization_pct, t.packet_loss_pct, t.latency_ms, t.cpu_utilization_pct, t.queue_drops, t.crc_errors):
                if val is not None and isinstance(val, (int, float)):
                    known_numbers.add(float(val))

        # 2. Check if a cross-query clarification step should be performed
        # e.g., if multiple devices are affected and a potential bottleneck uplink exists
        clarification_req: Optional[AgentMessage] = None
        clarification_resp: Optional[AgentMessage] = None

        perf_msg = next((m for m in findings if m.source_agent == AgentRole.PERFORMANCE_AGENT), None)
        conn_msg = next((m for m in findings if m.source_agent == AgentRole.CONNECTIVITY_AGENT), None)

        suspected_bottleneck = None
        if conn_msg and conn_msg.device_ids:
            suspected_bottleneck = conn_msg.device_ids[0]
        elif perf_msg and perf_msg.device_ids:
            suspected_bottleneck = perf_msg.device_ids[0]

        has_anomalies = any(m.severity != SeverityLevel.LOW for m in findings)
        if connectivity_agent_handler and has_anomalies and suspected_bottleneck and len(all_affected) >= 2:
            # Construct clarification request to Connectivity Agent
            clarification_req = self.create_message(
                session_id=session_id,
                target_agent=AgentRole.CONNECTIVITY_AGENT,
                message_type=MessageType.CLARIFICATION_REQUEST,
                finding=f"Clarification query: verify if {len(all_affected)} affected devices funnel through upstream node '{suspected_bottleneck}'",
                device_ids=list(all_affected),
                severity=SeverityLevel.MEDIUM,
                metadata={
                    "suspected_bottleneck": suspected_bottleneck,
                    "target_devices": list(all_affected),
                },
            )

            # Invoke Connectivity Agent directly for interactive collaboration
            try:
                clarification_resp = await connectivity_agent_handler(
                    clarification_req, telemetry, topology
                )
                if clarification_resp:
                    all_evidence.extend(clarification_resp.evidence)
            except Exception:
                clarification_resp = None

        # 3. Deterministic Hypothesis Scoring
        top_hyp, confidence, status, ranking, limitations = HypothesisScoringEngine.evaluate(
            findings=findings,
            clarification=clarification_resp,
            degraded_agents=degraded_agents,
            telemetry=telemetry,
        )

        # 4. Generate Narrative & Root Cause Phrasing
        suspected_root_cause = self._synthesize_root_cause_phrase(top_hyp, findings, suspected_bottleneck, status)
        narrative = self.llm_client.generate_narrative(
            top_hypothesis=top_hyp,
            confidence=confidence,
            findings=findings,
            affected_devices=list(all_affected),
            known_numbers=known_numbers,
        )

        # 5. Extract Alternative Causes
        alternatives = [h.hypothesis for h in ranking[1:4] if h.score >= 0.20]
        if not alternatives:
            alternatives = ["Transient upstream route oscillation", "Microburst buffer starvation"]

        # 6. Prioritized Recommended Checks / Remediation actions
        recommended_actions = self._generate_recommendations(top_hyp, suspected_bottleneck, status)

        consolidated_msg = self.create_message(
            session_id=session_id,
            target_agent=AgentRole.REPORTING_AGENT,
            message_type=MessageType.CONSOLIDATED_DIAGNOSIS,
            finding=narrative,
            severity=SeverityLevel.LOW if status == DiagnosisStatus.NO_FAULT_DETECTED else (
                SeverityLevel.HIGH if confidence > 0.75 else SeverityLevel.MEDIUM
            ),
            device_ids=[] if status == DiagnosisStatus.NO_FAULT_DETECTED else list(all_affected),
            metric="diagnostic_confidence",
            value=confidence,
            unit="ratio",
            evidence=all_evidence,
            confidence=confidence,
            possible_causes=alternatives,
            recommended_checks=recommended_actions,
            metadata={
                "suspected_root_cause": suspected_root_cause,
                "diagnostic_status": status.value,
                "hypotheses_ranking": [h.model_dump() for h in ranking],
                "limitations": limitations,
                "contributing_agents": sorted(list(contributing_agents)),
                "cross_query_conducted": clarification_resp is not None,
                "suspected_bottleneck": suspected_bottleneck,
            },
        )

        return consolidated_msg, clarification_req, clarification_resp

    def _synthesize_root_cause_phrase(
        self, top_hyp: str, findings: List[AgentMessage], bottleneck: Optional[str], status: Optional[DiagnosisStatus] = None
    ) -> str:
        if status in (DiagnosisStatus.INSUFFICIENT_EVIDENCE, DiagnosisStatus.INSUFFICIENT_DATA) or "Insufficient" in top_hyp:
            return "Insufficient telemetry: critical performance metrics missing to determine root cause"
        elif status == DiagnosisStatus.AMBIGUOUS or "Ambiguous" in top_hyp:
            return "Ambiguous multi-factor degradation: available evidence is insufficient to determine a unique root cause"
        elif "Congestion" in top_hyp:
            dev_label = f" on {bottleneck}" if bottleneck else ""
            return f"Severe link congestion and egress buffer queue saturation{dev_label}"
        elif "Interface or Link Down" in top_hyp:
            dev_label = f" on {bottleneck}" if bottleneck else ""
            return f"Physical link or interface failure causing path isolation{dev_label}"
        elif "CRC Framing" in top_hyp:
            dev_label = f" on {bottleneck}" if bottleneck else ""
            return f"Physical layer framing corruption and cable/transceiver degradation{dev_label}"
        elif "Resource Exhaustion" in top_hyp or "Overload" in top_hyp:
            dev_label = f" on {bottleneck}" if bottleneck else ""
            return f"Device control plane resource exhaustion (CPU/Memory){dev_label}"
        elif "Normal" in top_hyp:
            return "No significant network fault detected; all telemetry metrics within baseline"
        else:
            return f"Ambiguous multi-factor degradation: available evidence is insufficient to determine a unique root cause"

    def _generate_recommendations(self, top_hyp: str, bottleneck: Optional[str], status: Optional[DiagnosisStatus] = None) -> List[str]:
        target = f" on {bottleneck}" if bottleneck else ""
        if status in (DiagnosisStatus.INSUFFICIENT_EVIDENCE, DiagnosisStatus.INSUFFICIENT_DATA) or "Insufficient" in top_hyp:
            return [
                "Verify and re-enable telemetry streaming collectors across monitored switches",
                "Deploy continuous SNMP polling for IF-MIB interface utilization and packet drop counters",
                "Validate network management station polling reachability to access nodes",
            ]
        elif status == DiagnosisStatus.AMBIGUOUS or "Ambiguous" in top_hyp:
            return [
                "Deploy on-site TAP or SPAN port packet capture to isolate intermittent anomalies",
                "Audit upstream transit provider peering interfaces and traceroute hop-by-hop latency",
                "Enable per-flow telemetry (IPFIX/NetFlow) to evaluate non-buffer packet discards",
            ]
        elif "Congestion" in top_hyp:
            return [
                f"Inspect upstream and egress link utilization{target}",
                "Review queue configuration, WRED thresholds, and traffic distribution",
                "Apply rate-limiting or traffic shaping to non-critical bulk flows",
            ]
        elif "Interface or Link Down" in top_hyp:
            return [
                f"Verify physical cable seating and SFP optical transceiver health{target}",
                "Check STP spanning-tree topology and OSPF adjacency failover state",
                "Inspect interface error logs and administrative status",
            ]
        elif "CRC Framing" in top_hyp:
            return [
                f"Clean optical fiber end-faces and test optical link budget{target}",
                "Replace suspect patch cable connecting to the affected interface",
                "Verify speed and duplex autonegotiation parameters",
            ]
        elif "Resource Exhaustion" in top_hyp or "Overload" in top_hyp:
            return [
                f"Execute 'show processes cpu sorted' to identify runaway processes{target}",
                "Audit SNMP/telemetry polling intervals to reduce management plane overhead",
                "Verify control plane policing (CoPP) rules",
            ]
        else:
            return [
                "Deploy on-site TAP or SPAN port packet capture to isolate intermittent anomalies",
                "Monitor baseline telemetry trends across adjacent aggregation switches",
            ]
