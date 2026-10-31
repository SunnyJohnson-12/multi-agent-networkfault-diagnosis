from typing import List, Optional, Dict, Any
from app.agents.base_agent import BaseAgent
from app.models.messages import AgentRole, MessageType, SeverityLevel, EvidenceItem, AgentMessage
from app.models.telemetry import DeviceTelemetry
from app.models.topology import CampusTopology


class InfrastructureAgent(BaseAgent):
    """Specialized agent analyzing CPU, memory, interface status, queue drops, and CRC hardware errors."""

    def __init__(self):
        super().__init__(AgentRole.INFRASTRUCTURE_AGENT)

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

        max_cpu = 0.0
        max_mem = 0.0
        total_queue_drops = 0
        total_crc_errors = 0
        down_interfaces: List[str] = []
        worst_cpu_device = None

        for rec in telemetry:
            is_device_affected = False
            baseline = rec.baseline

            # 1. Interface Operational Status
            if rec.interface_status in ("down", "admin_down", "degraded"):
                is_device_affected = True
                down_interfaces.append(f"{rec.device_id}:{rec.interface or 'intf'}")
                evidence_items.append(
                    EvidenceItem(
                        metric="interface_status",
                        value=rec.interface_status,
                        interpretation=f"Interface is in '{rec.interface_status}' state (link down)",
                        device_id=rec.device_id,
                    )
                )
                possible_causes.append("Physical cable disconnect, SFP transceiver failure, or remote peer shutdown")
                recommended_checks.append("Verify physical cable patch connection and SFP optical power levels")

            # 2. Queue drops (egress buffer exhaustion)
            if rec.queue_drops > 0:
                is_device_affected = True
                total_queue_drops += rec.queue_drops
                base_drops = baseline.baseline_queue_drops if baseline else 0
                evidence_items.append(
                    EvidenceItem(
                        metric="queue_drops",
                        value=rec.queue_drops,
                        interpretation=f"Elevated egress queue drops ({rec.queue_drops:,} packets) due to buffer exhaustion",
                        baseline=base_drops,
                        device_id=rec.device_id,
                    )
                )
                possible_causes.append("Hardware egress queue full; microbursts exceeding switch buffer depth")

            # 3. CRC Errors (Layer 1 framing / cable / transceiver defects)
            if rec.crc_errors > 0:
                is_device_affected = True
                total_crc_errors += rec.crc_errors
                base_crc = baseline.baseline_crc_errors if baseline else 0
                evidence_items.append(
                    EvidenceItem(
                        metric="crc_errors",
                        value=rec.crc_errors,
                        interpretation=f"Physical layer framing corruption ({rec.crc_errors:,} CRC errors)",
                        baseline=base_crc,
                        device_id=rec.device_id,
                    )
                )
                possible_causes.append("Dirty fiber connector, faulty patch cable, or duplex mismatch causing CRC errors")
                recommended_checks.append("Clean optical connectors, inspect patch lead, and verify auto-negotiation duplex")

            # 4. CPU Utilization
            cpu = rec.cpu_utilization_pct
            base_cpu = baseline.baseline_cpu_utilization_pct if baseline else None
            if cpu > max_cpu:
                max_cpu = cpu
                worst_cpu_device = rec.device_id

            if cpu >= 85.0:
                is_device_affected = True
                evidence_items.append(
                    EvidenceItem(
                        metric="cpu_utilization_pct",
                        value=round(cpu, 1),
                        interpretation=f"Critical CPU exhaustion ({cpu:.1f}%) on device control plane",
                        baseline=base_cpu,
                        device_id=rec.device_id,
                    )
                )
                possible_causes.append("Control plane process loop, ARP storm, or unthrottled management plane polling")
                recommended_checks.append("Examine 'show processes cpu sorted' to identify runaway tasks")
            elif cpu >= 70.0:
                evidence_items.append(
                    EvidenceItem(
                        metric="cpu_utilization_pct",
                        value=round(cpu, 1),
                        interpretation=f"Elevated device CPU utilization ({cpu:.1f}%)",
                        baseline=base_cpu,
                        device_id=rec.device_id,
                    )
                )

            # 5. Memory Utilization
            mem = rec.memory_utilization_pct
            base_mem = baseline.baseline_memory_utilization_pct if baseline else None
            if mem > max_mem:
                max_mem = mem
            if mem >= 85.0:
                is_device_affected = True
                evidence_items.append(
                    EvidenceItem(
                        metric="memory_utilization_pct",
                        value=round(mem, 1),
                        interpretation=f"Critical memory consumption ({mem:.1f}%)",
                        baseline=base_mem,
                        device_id=rec.device_id,
                    )
                )
                possible_causes.append("Memory leak or routing table exhaustion in RAM")

            if is_device_affected and rec.device_id not in affected_devices:
                affected_devices.append(rec.device_id)

        # Synthesize Infrastructure Finding with dynamic evidence-based confidence
        if down_interfaces:
            severity = SeverityLevel.CRITICAL
            finding = f"Interface down event detected: {', '.join(down_interfaces)} is non-operational."
            confidence = round(min(0.98, max(0.70, 0.82 + 0.12 * min(1.0, len(down_interfaces) / 3.0))), 2)
            primary_metric = "interface_status"
            primary_val = "down"
        elif total_crc_errors > 50:
            severity = SeverityLevel.HIGH
            finding = (
                f"Severe physical layer framing degradation: {total_crc_errors:,} CRC errors logged, "
                "indicating damaged physical cabling or failing transceiver optics."
            )
            crc_scale = min(1.0, (total_crc_errors - 50) / 200.0)
            confidence = round(min(0.94, max(0.60, 0.70 + 0.20 * crc_scale)), 2)
            primary_metric = "crc_errors"
            primary_val = total_crc_errors
        elif total_queue_drops > 1000:
            severity = SeverityLevel.CRITICAL if total_queue_drops > 10000 else SeverityLevel.HIGH
            finding = (
                f"Egress queue congestion: {total_queue_drops:,} queue drops logged across hardware buffers."
            )
            drops_scale = min(1.0, (total_queue_drops - 1000) / 15000.0)
            confidence = round(min(0.96, max(0.65, 0.72 + 0.20 * drops_scale)), 2)
            primary_metric = "queue_drops"
            primary_val = total_queue_drops
            recommended_checks.append("Audit switch QoS buffer thresholds (e.g. WRED, shared pool headroom)")
        elif max_cpu >= 85.0:
            severity = SeverityLevel.HIGH
            finding = f"Device resource exhaustion: CPU reached {max_cpu:.1f}% on {worst_cpu_device}."
            cpu_scale = min(1.0, (max_cpu - 85.0) / 15.0)
            confidence = round(min(0.92, max(0.60, 0.70 + 0.18 * cpu_scale)), 2)
            primary_metric = "cpu_utilization_pct"
            primary_val = round(max_cpu, 1)
        elif total_queue_drops > 0:
            severity = SeverityLevel.MEDIUM
            finding = f"Moderate buffer pressure: {total_queue_drops:,} queue drops observed."
            confidence = round(min(0.78, max(0.50, 0.58 + 0.18 * min(1.0, total_queue_drops / 1000.0))), 2)
            primary_metric = "queue_drops"
            primary_val = total_queue_drops
        else:
            severity = SeverityLevel.LOW
            finding = "Infrastructure health normal: CPU, memory, interfaces, and hardware buffers operating within limits."
            cleanliness = 1.0 - max(max_cpu / 100.0, max_mem / 100.0)
            confidence = round(min(0.95, max(0.70, 0.78 + 0.16 * cleanliness)), 2)
            primary_metric = "cpu_utilization_pct"
            primary_val = round(max_cpu, 1)

        return self.create_message(
            session_id=session_id,
            target_agent=AgentRole.ORCHESTRATOR,
            message_type=MessageType.DIAGNOSTIC_FINDING,
            finding=finding,
            severity=severity,
            device_ids=affected_devices or ([worst_cpu_device] if worst_cpu_device else []),
            metric=primary_metric,
            value=primary_val,
            unit="events" if "status" not in primary_metric else "",
            evidence=evidence_items,
            confidence=confidence,
            possible_causes=list(set(possible_causes)),
            recommended_checks=recommended_checks,
            metadata={
                "total_queue_drops": total_queue_drops,
                "total_crc_errors": total_crc_errors,
                "max_cpu_pct": round(max_cpu, 1),
                "max_mem_pct": round(max_mem, 1),
                "down_interfaces_count": len(down_interfaces),
            },
        )
