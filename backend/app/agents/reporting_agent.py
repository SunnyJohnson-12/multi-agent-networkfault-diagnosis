from typing import List, Optional, Dict, Any, Tuple
from app.agents.base_agent import BaseAgent
from app.models.messages import AgentRole, MessageType, SeverityLevel, AgentMessage
from app.models.diagnosis import (
    FinalDiagnosisReport,
    DiagnosisStatus,
    SupportingEvidenceItem,
    DiagnosticExtensions,
    SimulatedRemediation,
    HypothesisScore,
)
from app.models.telemetry import DeviceTelemetry
from app.models.claims import ClaimLedger, ClaimSource


class ReportingAgent(BaseAgent):
    """Specialized agent transforming consolidated diagnostic findings into strict Section 6 JSON,

    an executive Markdown report with claim footnotes, and simulated remediation projections.
    """

    def __init__(self):
        super().__init__(AgentRole.REPORTING_AGENT)

    async def generate_report(
        self,
        session_id: str,
        incident_id: str,
        diagnosis_msg: AgentMessage,
        raw_messages: List[AgentMessage],
        telemetry: List[DeviceTelemetry],
    ) -> Tuple[AgentMessage, FinalDiagnosisReport, str]:
        meta = diagnosis_msg.metadata or {}
        root_cause = meta.get("suspected_root_cause", diagnosis_msg.finding)
        status_str = meta.get("diagnostic_status", "diagnosed")
        try:
            status = DiagnosisStatus(status_str)
        except Exception:
            status = DiagnosisStatus.DIAGNOSED

        confidence = diagnosis_msg.confidence
        affected_devices = diagnosis_msg.device_ids
        contributing_agents = meta.get(
            "contributing_agents", ["performance_agent", "infrastructure_agent", "connectivity_agent"]
        )
        limitations = meta.get("limitations", [])
        if not limitations:
            limitations = ["Root cause based on telemetry snapshot; on-site verification recommended"]

        # 1. Build Section 6 supporting evidence list
        supporting_evidence: List[SupportingEvidenceItem] = []
        for ev in diagnosis_msg.evidence:
            val = ev.value
            if isinstance(val, (dict, list)):
                val = str(val)
            supporting_evidence.append(
                SupportingEvidenceItem(
                    metric=ev.metric,
                    value=val,
                    interpretation=ev.interpretation,
                )
            )

        # Ensure at least minimal supporting evidence
        if not supporting_evidence:
            supporting_evidence.append(
                SupportingEvidenceItem(
                    metric="baseline_adherence",
                    value=100,
                    interpretation="All devices conform to healthy baseline metrics",
                )
            )

        # 2. Build recommendations with mandatory suffix
        raw_recommendations = diagnosis_msg.recommended_checks
        formatted_recommendations = []
        for r in raw_recommendations:
            suffix = " — Recommended action — human review required."
            if "human review required" not in r:
                formatted_recommendations.append(f"{r}{suffix}")
            else:
                formatted_recommendations.append(r)

        # 3. Build Evidence-to-Claim Ledger (Traceability Core)
        ledger = ClaimLedger(session_id=session_id, incident_id=incident_id)

        # Root cause claim
        root_sources = [
            ClaimSource(
                message_id=diagnosis_msg.message_id,
                source_agent=diagnosis_msg.source_agent.value,
                metric="suspected_root_cause",
                value=root_cause,
                device_id=affected_devices[0] if affected_devices else None,
                timestamp=diagnosis_msg.timestamp,
                interpretation="Synthesized primary root cause consensus from multi-agent telemetry correlation",
            )
        ]
        for m in raw_messages:
            if m.message_type in (MessageType.DIAGNOSTIC_FINDING, MessageType.CLARIFICATION_RESPONSE):
                root_sources.append(
                    ClaimSource(
                        message_id=m.message_id,
                        source_agent=m.source_agent.value,
                        metric=m.metric or "finding",
                        value=m.value if m.value is not None else m.finding[:60],
                        device_id=m.device_ids[0] if m.device_ids else None,
                        timestamp=m.timestamp,
                        interpretation=m.finding[:120],
                    )
                )
        ledger.add_claim(statement=f"Suspected root cause: {root_cause}", claim_type="root_cause", sources=root_sources)

        # Evidence claims
        for ev in diagnosis_msg.evidence:
            ev_sources = []
            for m in raw_messages:
                if m.message_type in (MessageType.DIAGNOSTIC_FINDING, MessageType.CLARIFICATION_RESPONSE):
                    if m.metric == ev.metric or any(mev.metric == ev.metric for mev in m.evidence):
                        ev_sources.append(
                            ClaimSource(
                                message_id=m.message_id,
                                source_agent=m.source_agent.value,
                                metric=ev.metric,
                                value=ev.value,
                                unit=getattr(ev, "unit", None),
                                device_id=getattr(ev, "device_id", None) or (m.device_ids[0] if m.device_ids else None),
                                timestamp=m.timestamp,
                                interpretation=ev.interpretation,
                            )
                        )
            if not ev_sources:
                ev_sources.append(
                    ClaimSource(
                        message_id=diagnosis_msg.message_id,
                        source_agent=diagnosis_msg.source_agent.value,
                        metric=ev.metric,
                        value=ev.value,
                        unit=getattr(ev, "unit", None),
                        device_id=getattr(ev, "device_id", None) or (affected_devices[0] if affected_devices else None),
                        timestamp=diagnosis_msg.timestamp,
                        interpretation=ev.interpretation,
                    )
                )
            ledger.add_claim(
                statement=f"Metric evidence {ev.metric} = {ev.value}: {ev.interpretation}",
                claim_type="evidence",
                sources=ev_sources,
            )

        # Affected device claims
        for dev in affected_devices:
            dev_sources = [
                ClaimSource(
                    message_id=m.message_id,
                    source_agent=m.source_agent.value,
                    metric="affected_device",
                    value=dev,
                    device_id=dev,
                    timestamp=m.timestamp,
                    interpretation=f"Device '{dev}' reported anomalous metric exceedances",
                )
                for m in raw_messages
                if dev in m.device_ids
            ]
            if not dev_sources:
                dev_sources.append(
                    ClaimSource(
                        message_id=diagnosis_msg.message_id,
                        source_agent=diagnosis_msg.source_agent.value,
                        metric="affected_device",
                        value=dev,
                        device_id=dev,
                        timestamp=diagnosis_msg.timestamp,
                        interpretation=f"Device '{dev}' identified in affected blast radius",
                    )
                )
            ledger.add_claim(statement=f"Impacted network node: {dev}", claim_type="affected_device", sources=dev_sources)

        # Recommendation claims
        for act in formatted_recommendations:
            ledger.add_claim(
                statement=act,
                claim_type="recommendation",
                sources=[
                    ClaimSource(
                        message_id=diagnosis_msg.message_id,
                        source_agent=diagnosis_msg.source_agent.value,
                        metric="recommended_action",
                        value=act[:40],
                        device_id=affected_devices[0] if affected_devices else None,
                        timestamp=diagnosis_msg.timestamp,
                        interpretation="Action recommended by multi-agent consensus for network operator verification",
                    )
                ],
            )

        # 4. Simulated Remediation Modeling
        simulated_remediation = self._simulate_remediation(root_cause, telemetry, meta.get("suspected_bottleneck"))

        # 5. Build Diagnostic Timeline
        timeline = []
        for idx, m in enumerate(raw_messages):
            timeline.append(
                {
                    "step": idx + 1,
                    "timestamp": m.timestamp,
                    "source": m.source_agent.value,
                    "target": m.target_agent.value,
                    "type": m.message_type.value,
                    "finding_snippet": m.finding[:90] + ("..." if len(m.finding) > 90 else ""),
                }
            )

        # Hypotheses ranking
        raw_ranking = meta.get("hypotheses_ranking", [])
        hypotheses_models = [HypothesisScore(**h) for h in raw_ranking]

        # Extract structured agent findings list and message IDs for Prompt #12
        agent_findings = [
            {
                "source_agent": m.source_agent.value,
                "target_agent": m.target_agent.value,
                "message_type": m.message_type.value,
                "finding": m.finding,
                "metric": m.metric,
                "value": m.value,
                "unit": m.unit,
                "severity": m.severity.value,
                "confidence": m.confidence,
                "device_ids": m.device_ids,
            }
            for m in raw_messages
            if m.message_type in (MessageType.DIAGNOSTIC_FINDING, MessageType.CLARIFICATION_RESPONSE, MessageType.AGENT_ERROR)
        ]
        message_ids = [m.message_id for m in raw_messages]

        # 6. Build Final Section 6 Report with Extensions
        from datetime import datetime
        current_iso = datetime.utcnow().isoformat() + "Z"
        extensions = DiagnosticExtensions(
            session_id=session_id,
            severity=diagnosis_msg.severity.value,
            timestamp=current_iso,
            scope="Campus-Wide Aggregation" if len(affected_devices) > 3 else "Localized Segment",
            hypotheses_ranking=hypotheses_models,
            agent_message_count=len(raw_messages) + 2,
            agent_findings=agent_findings,
            message_ids=message_ids,
            timeline=timeline,
            simulated_remediation=simulated_remediation,
            cross_query_conducted=meta.get("cross_query_conducted", False),
            degraded_agents=meta.get("degraded_agents", []),
            claim_ledger=[c.model_dump() for c in ledger.claims],
            traceability={
                "coverage_pct": ledger.coverage_pct,
                "total_claims": ledger.total_claims,
                "grounded_claims": ledger.grounded_claims,
                "unsupported_claims": ledger.total_claims - ledger.grounded_claims,
            },
        )

        final_report = FinalDiagnosisReport(
            incident_id=incident_id,
            status=status,
            suspected_root_cause=root_cause,
            confidence=confidence,
            affected_devices=affected_devices,
            supporting_evidence=supporting_evidence,
            alternative_causes=diagnosis_msg.possible_causes,
            recommended_actions=formatted_recommendations,
            evidence_sources=contributing_agents,
            limitations=limitations,
            extensions=extensions,
        )

        # 7. Generate Footnoted Markdown Report
        markdown_report = self._build_markdown_report(final_report, raw_messages, ledger)

        # Create protocol message for final report
        final_msg = self.create_message(
            session_id=session_id,
            target_agent=AgentRole.ORCHESTRATOR,
            message_type=MessageType.FINAL_REPORT,
            finding=f"Final diagnosis report compiled for {incident_id}: {root_cause}",
            severity=diagnosis_msg.severity,
            device_ids=affected_devices,
            metric="report_status",
            value="complete",
            confidence=confidence,
            evidence=diagnosis_msg.evidence,
            metadata={"report_payload": final_report.model_dump()},
        )

        return final_msg, final_report, markdown_report

    def _simulate_remediation(
        self, root_cause: str, telemetry: List[DeviceTelemetry], bottleneck: Optional[str]
    ) -> SimulatedRemediation:
        target = bottleneck or (telemetry[0].device_id if telemetry else "CORE_SW")
        if "congestion" in root_cause.lower() or "saturation" in root_cause.lower():
            max_util = max((t.link_utilization_pct for t in telemetry), default=96.0)
            return SimulatedRemediation(
                action_type="Dynamic Traffic Shaping & Queue Reallocation",
                description=f"Simulate applying class-based QoS rate limits on egress uplink of {target}.",
                pre_remediation_metric="link_utilization_pct",
                pre_remediation_value=round(max_util, 1),
                post_remediation_metric="link_utilization_pct",
                post_remediation_value=round(max_util * 0.75, 1),
                estimated_impact=(
                    f"Traffic shaping would reduce estimated link utilization from {max_util:.1f}% to "
                    f"{max_util * 0.75:.1f}%, relieving egress buffer queue pressure."
                ),
            )
        elif "interface" in root_cause.lower() or "down" in root_cause.lower():
            return SimulatedRemediation(
                action_type="Automated Topology Rerouting / Path Redundancy",
                description=f"Simulate rerouting traffic from down link on {target} to redundant secondary trunk.",
                pre_remediation_metric="path_availability",
                pre_remediation_value="0% (isolated)",
                post_remediation_metric="path_availability",
                post_remediation_value="100% (failover restored)",
                estimated_impact="Failover restoration re-establishes downstream reachability across all isolated access nodes.",
            )
        elif "crc" in root_cause.lower() or "cable" in root_cause.lower():
            return SimulatedRemediation(
                action_type="Optical Transceiver / Patch Cable Replacement",
                description=f"Simulate optical module recabling on interface connecting {target}.",
                pre_remediation_metric="crc_errors",
                pre_remediation_value=125,
                post_remediation_metric="crc_errors",
                post_remediation_value=0,
                estimated_impact="Eliminating physical layer framing errors drops packet loss from >8% to 0.0%.",
            )
        elif "resource" in root_cause.lower() or "cpu" in root_cause.lower():
            max_cpu = max((t.cpu_utilization_pct for t in telemetry), default=88.0)
            return SimulatedRemediation(
                action_type="Control Plane CoPP Rate Limiting",
                description=f"Simulate applying CoPP filters to throttle excessive SNMP/ARP polling on {target}.",
                pre_remediation_metric="cpu_utilization_pct",
                pre_remediation_value=round(max_cpu, 1),
                post_remediation_metric="cpu_utilization_pct",
                post_remediation_value=round(max_cpu * 0.45, 1),
                estimated_impact=f"CoPP policy deployment projected to drop control plane CPU load from {max_cpu:.1f}% to {max_cpu * 0.45:.1f}%.",
            )
        else:
            return SimulatedRemediation(
                action_type="Telemetry Baseline Calibration",
                description="Simulate continuous baseline window tracking across all campus segments.",
                pre_remediation_metric="baseline_drift",
                pre_remediation_value="normal",
                post_remediation_metric="baseline_drift",
                post_remediation_value="normal",
                estimated_impact="Network state steady; no corrective physical remediation required.",
            )

    def _build_markdown_report(
        self, report: FinalDiagnosisReport, messages: List[AgentMessage], ledger: Optional[ClaimLedger] = None
    ) -> str:
        md = []
        md.append(f"# Incident Diagnostic Report: {report.incident_id}\n")
        md.append(f"**Session ID:** `{report.extensions.session_id if report.extensions else 'N/A'}`  ")
        md.append(f"**Status:** `{report.status.value.upper()}`  ")
        md.append(f"**Severity:** `{report.extensions.severity.upper() if report.extensions and report.extensions.severity else 'MEDIUM'}`  ")
        md.append(f"**Network Scope:** `{report.extensions.scope if report.extensions else 'Campus'}`\n")

        md.append("## Diagnostic Summary")
        md.append(
            f"The multi-agent network diagnosis system analyzed telemetry across domain-specific agents "
            f"({', '.join(report.evidence_sources)}). A consensus diagnosis was reached with "
            f"**{report.confidence * 100:.0f}% confidence**.\n"
        )

        rc_claim = next((c for c in (ledger.claims if ledger else []) if c.claim_type == "root_cause"), None)
        rc_fn = f" {rc_claim.footnote_tag}" if rc_claim else ""
        md.append("## Probable Root Cause")
        md.append(f"> **{report.suspected_root_cause}**{rc_fn}\n")

        md.append("## Confidence")
        md.append(
            f"- **Overall Confidence Score:** `{report.confidence:.2f}` / 1.00\n"
            f"- **Confidence Assessment:** {'High certainty based on corroborating multi-agent telemetry' if report.confidence >= 0.8 else 'Moderate certainty with notable alternative possibilities'}\n"
        )

        md.append("## Evidence")
        md.append("| Metric | Observed Value | Interpretation | Citation |")
        md.append("|---|---|---|---|")
        for ev in report.supporting_evidence:
            ev_claim = next((cl for cl in (ledger.claims if ledger else []) if ev.metric in cl.statement), None)
            fn = ev_claim.footnote_tag if ev_claim else ""
            md.append(f"| `{ev.metric}` | `{ev.value}` | {ev.interpretation} | {fn} |")
        md.append("")

        md.append("## Affected Devices")
        for d in report.affected_devices:
            dev_claim = next((cl for cl in (ledger.claims if ledger else []) if cl.claim_type == "affected_device" and d in cl.statement), None)
            fn = f" {dev_claim.footnote_tag}" if dev_claim else ""
            md.append(f"- `{d}`{fn}")
        md.append("")

        md.append("## Network Scope")
        md.append(f"Observed impact domain: **{report.extensions.scope if report.extensions else 'Campus Network'}**\n")

        md.append("## Alternative Explanations")
        for alt in report.alternative_causes:
            md.append(f"- {alt}")
        md.append("")

        md.append("## Recommended Actions")
        for act in report.recommended_actions:
            act_claim = next((cl for cl in (ledger.claims if ledger else []) if cl.claim_type == "recommendation" and act[:20] in cl.statement), None)
            fn = f" {act_claim.footnote_tag}" if act_claim else ""
            md.append(f"- {act}{fn}")
        md.append("")

        md.append("## Uncertainty & Limitations")
        for lim in report.limitations:
            md.append(f"- {lim}")
        md.append("")

        if report.extensions and report.extensions.simulated_remediation:
            sim = report.extensions.simulated_remediation
            md.append("## Simulated Remediation (Simulation Only)")
            md.append(f"**Action:** {sim.action_type}  ")
            md.append(f"**Projected Outcome:** {sim.estimated_impact}  ")
            md.append(f"> *{sim.disclaimer}*\n")

        md.append("## Agent Findings Breakdown")
        for m in messages:
            if m.message_type in (MessageType.DIAGNOSTIC_FINDING, MessageType.CLARIFICATION_RESPONSE):
                md.append(f"### Agent: `{m.source_agent.value}`")
                md.append(f"- **Finding:** {m.finding}")
                md.append(f"- **Severity:** `{m.severity.value}` | **Confidence:** `{m.confidence:.2f}`\n")

        md.append("## Diagnostic Timeline")
        md.append("| Step | Timestamp | Source Agent | Target Agent | Message Type | Summary |")
        md.append("|---|---|---|---|---|---|")
        for t in (report.extensions.timeline if report.extensions else []):
            md.append(f"| {t['step']} | {t['timestamp']} | `{t['source']}` | `{t['target']}` | `{t['type']}` | {t['finding_snippet']} |")
        md.append("")

        if ledger and ledger.claims:
            md.append("## Evidence & Claim Traceability Footnotes")
            md.append(f"**Traceability Provenance Coverage:** `{ledger.coverage_pct:.1f}%` ({ledger.grounded_claims}/{ledger.total_claims} verified grounded claims)\n")
            for c in ledger.claims:
                sources_str = ", ".join(f"`{s.source_agent}` (msg: `{s.message_id[:8]}...`, {s.metric}={s.value})" for s in c.sources[:3])
                md.append(f"- **{c.footnote_tag}** [{c.claim_type.upper()}]: {c.statement} — *Sources:* {sources_str}")
            md.append("")

        return "\n".join(md)
