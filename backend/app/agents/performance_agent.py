from typing import List, Optional, Dict, Any
from app.agents.base_agent import BaseAgent
from app.models.messages import AgentRole, MessageType, SeverityLevel, EvidenceItem, AgentMessage
from app.models.telemetry import DeviceTelemetry
from app.models.topology import CampusTopology


class PerformanceAgent(BaseAgent):
    """Specialized agent analyzing latency, jitter, packet loss, bandwidth, and link utilization."""

    def __init__(self):
        super().__init__(AgentRole.PERFORMANCE_AGENT)

    async def analyze(
        self,
        session_id: str,
        telemetry: List[DeviceTelemetry],
        topology: Optional[CampusTopology] = None,
    ) -> AgentMessage:
        evidence_items: List[EvidenceItem] = []
        possible_causes: List[str] = []
        recommended_checks: List[str] = []
        affected_devices: List[str] = []

        max_utilization = 0.0
        max_latency = 0.0
        max_loss = 0.0
        max_jitter = 0.0

        worst_device = None

        for rec in telemetry:
            is_device_affected = False
            baseline = rec.baseline

            # 1. Link utilization analysis
            util = rec.link_utilization_pct
            base_util = baseline.baseline_link_utilization_pct if baseline else None
            if util > max_utilization:
                max_utilization = util
                worst_device = rec.device_id

            if util >= 90.0:
                is_device_affected = True
                interpretation = f"Critical link saturation ({util:.1f}% >= 90% threshold)"
                if base_util is not None:
                    interpretation += f", baseline was {base_util:.1f}%"
                evidence_items.append(
                    EvidenceItem(
                        metric="link_utilization_pct",
                        value=round(util, 1),
                        interpretation=interpretation,
                        baseline=base_util,
                        device_id=rec.device_id,
                    )
                )
                possible_causes.append("Excessive network traffic saturating physical uplink capacity")
            elif util >= 75.0:
                is_device_affected = True
                evidence_items.append(
                    EvidenceItem(
                        metric="link_utilization_pct",
                        value=round(util, 1),
                        interpretation=f"Elevated link utilization ({util:.1f}%)",
                        baseline=base_util,
                        device_id=rec.device_id,
                    )
                )

            # 2. Packet loss analysis
            loss = rec.packet_loss_pct
            base_loss = baseline.baseline_packet_loss_pct if baseline else None
            if loss > max_loss:
                max_loss = loss

            if loss >= 5.0:
                is_device_affected = True
                evidence_items.append(
                    EvidenceItem(
                        metric="packet_loss_pct",
                        value=round(loss, 2),
                        interpretation=f"Severe packet drop rate ({loss:.2f}%)",
                        baseline=base_loss,
                        device_id=rec.device_id,
                    )
                )
                possible_causes.append("Buffer tail drop or degraded transmission medium causing packet loss")
            elif loss >= 1.5:
                is_device_affected = True
                evidence_items.append(
                    EvidenceItem(
                        metric="packet_loss_pct",
                        value=round(loss, 2),
                        interpretation=f"Moderate packet loss ({loss:.2f}%) exceeding normal baseline",
                        baseline=base_loss,
                        device_id=rec.device_id,
                    )
                )

            # 3. Latency analysis
            lat = rec.latency_ms
            base_lat = baseline.baseline_latency_ms if baseline else None
            if lat > max_latency:
                max_latency = lat

            if lat >= 100.0:
                is_device_affected = True
                interpretation = f"Severe round-trip latency ({lat:.1f} ms)"
                if base_lat is not None:
                    interpretation += f" (baseline was {base_lat:.1f} ms)"
                evidence_items.append(
                    EvidenceItem(
                        metric="latency_ms",
                        value=round(lat, 1),
                        interpretation=interpretation,
                        baseline=base_lat,
                        device_id=rec.device_id,
                    )
                )
            elif lat >= 45.0:
                evidence_items.append(
                    EvidenceItem(
                        metric="latency_ms",
                        value=round(lat, 1),
                        interpretation=f"Elevated transmission latency ({lat:.1f} ms)",
                        baseline=base_lat,
                        device_id=rec.device_id,
                    )
                )

            # 4. Jitter analysis
            jit = rec.jitter_ms
            base_jit = baseline.baseline_jitter_ms if baseline else None
            if jit > max_jitter:
                max_jitter = jit
            if jit >= 25.0:
                is_device_affected = True
                evidence_items.append(
                    EvidenceItem(
                        metric="jitter_ms",
                        value=round(jit, 1),
                        interpretation=f"High latency jitter ({jit:.1f} ms) indicating buffer queuing oscillation",
                        baseline=base_jit,
                        device_id=rec.device_id,
                    )
                )

            if is_device_affected and rec.device_id not in affected_devices:
                affected_devices.append(rec.device_id)

        # Synthesize Performance Finding with dynamic evidence-based confidence
        if max_utilization >= 90.0 and max_loss >= 3.0:
            severity = SeverityLevel.CRITICAL
            finding = (
                f"Severe link congestion detected on {worst_device or 'network uplink'} "
                f"with {max_utilization:.1f}% utilization, {max_loss:.1f}% packet loss, "
                f"and latency spike to {max_latency:.1f} ms."
            )
            # Dynamic confidence based on excess utilization, packet loss, and latency
            util_factor = (max_utilization - 90.0) / 10.0
            loss_factor = min(1.0, max_loss / 10.0)
            lat_factor = min(1.0, max_latency / 200.0)
            confidence = round(min(0.96, max(0.50, 0.62 + 0.18 * util_factor + 0.12 * loss_factor + 0.04 * lat_factor)), 2)
            recommended_checks.extend(
                [
                    "Inspect top talkers and per-flow bandwidth consumption via NetFlow/IPFIX",
                    "Verify QoS queue allocations and egress rate-limiters",
                ]
            )
        elif max_loss >= 5.0 and max_utilization < 60.0:
            severity = SeverityLevel.HIGH
            finding = (
                f"Significant packet loss ({max_loss:.1f}%) observed despite low link utilization ({max_utilization:.1f}%), "
                "suggesting non-bandwidth transmission degradation or faulty physical medium."
            )
            loss_factor = min(1.0, (max_loss - 5.0) / 10.0)
            confidence = round(min(0.92, max(0.50, 0.66 + 0.20 * loss_factor + 0.06 * (1.0 - max_utilization / 100.0))), 2)
            recommended_checks.append("Inspect physical interface error counters and CRC framing integrity")
        elif max_latency >= 100.0:
            severity = SeverityLevel.HIGH
            finding = (
                f"Elevated network latency reaching {max_latency:.1f} ms with jitter {max_jitter:.1f} ms."
            )
            lat_factor = min(1.0, (max_latency - 100.0) / 150.0)
            confidence = round(min(0.88, max(0.50, 0.62 + 0.22 * lat_factor)), 2)
            recommended_checks.append("Trace network path hop-by-hop to identify latency accumulation hop")
        elif max_utilization >= 75.0:
            severity = SeverityLevel.MEDIUM
            finding = f"Moderate traffic congestion: link utilization peaked at {max_utilization:.1f}%."
            util_factor = (max_utilization - 75.0) / 15.0
            confidence = round(min(0.78, max(0.45, 0.55 + 0.20 * util_factor)), 2)
            recommended_checks.append("Monitor link utilization trends for impending saturation")
        else:
            severity = SeverityLevel.LOW
            finding = "All performance metrics (latency, jitter, packet loss, throughput) within normal operating baselines."
            headroom = 1.0 - max(max_utilization / 100.0, max_loss / 10.0)
            confidence = round(min(0.95, max(0.65, 0.76 + 0.18 * headroom)), 2)

        return self.create_message(
            session_id=session_id,
            target_agent=AgentRole.ORCHESTRATOR,
            message_type=MessageType.DIAGNOSTIC_FINDING,
            finding=finding,
            severity=severity,
            device_ids=affected_devices or ([worst_device] if worst_device else []),
            metric="link_utilization_pct",
            value=round(max_utilization, 1),
            unit="%",
            evidence=evidence_items,
            confidence=confidence,
            possible_causes=list(set(possible_causes)),
            recommended_checks=recommended_checks,
            metadata={
                "max_latency_ms": round(max_latency, 1),
                "max_loss_pct": round(max_loss, 2),
                "max_jitter_ms": round(max_jitter, 1),
                "max_utilization_pct": round(max_utilization, 1),
                "analyzed_records_count": len(telemetry),
            },
        )
