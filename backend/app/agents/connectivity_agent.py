import networkx as nx
from typing import List, Optional, Dict, Any, Set
from app.agents.base_agent import BaseAgent
from app.models.messages import AgentRole, MessageType, SeverityLevel, EvidenceItem, AgentMessage
from app.models.telemetry import DeviceTelemetry
from app.models.topology import CampusTopology


class ConnectivityAgent(BaseAgent):
    """Specialized agent analyzing campus topology, dependency blast radius, and common bottleneck uplinks."""

    def __init__(self):
        super().__init__(AgentRole.CONNECTIVITY_AGENT)

    def _build_graph(self, topology: CampusTopology) -> nx.DiGraph:
        g = nx.DiGraph()
        for node in topology.nodes:
            g.add_node(
                node.node_id,
                name=node.name,
                node_type=node.node_type,
                segment=node.segment,
                status=node.status,
            )
        for link in topology.links:
            # Directed edge from source to target (downstream) and target to source (upstream)
            g.add_edge(
                link.source_node,
                link.target_node,
                link_id=link.link_id,
                is_uplink=link.is_uplink,
                bandwidth_mbps=link.bandwidth_mbps,
                status=link.status,
            )
            # Bidirectional connectivity
            g.add_edge(
                link.target_node,
                link.source_node,
                link_id=f"{link.link_id}_rev",
                is_uplink=not link.is_uplink,
                bandwidth_mbps=link.bandwidth_mbps,
                status=link.status,
            )
        return g

    async def analyze(
        self,
        session_id: str,
        telemetry: List[DeviceTelemetry],
        topology: Optional[CampusTopology] = None,
    ) -> AgentMessage:
        if not topology or not topology.nodes:
            return self.create_message(
                session_id=session_id,
                target_agent=AgentRole.ORCHESTRATOR,
                message_type=MessageType.DIAGNOSTIC_FINDING,
                finding="Topology information unavailable; unable to assess blast radius or graph dependencies.",
                severity=SeverityLevel.LOW,
                confidence=0.3,
            )

        g = self._build_graph(topology)
        evidence_items: List[EvidenceItem] = []
        possible_causes: List[str] = []
        recommended_checks: List[str] = []

        # Identify all devices reporting telemetry anomalies
        degraded_devices = [
            t.device_id
            for t in telemetry
            if (
                t.packet_loss_pct >= 2.0
                or t.latency_ms >= 50.0
                or t.interface_status in ("down", "degraded")
                or t.queue_drops > 100
                or t.crc_errors > 20
                or t.link_utilization_pct >= 85.0
            )
        ]

        # Calculate shared upstream bottlenecks
        common_ancestors: Dict[str, int] = {}
        shared_uplink_node = None
        max_shared_count = 0

        for dev in degraded_devices:
            if dev in g:
                # Predecessors in directed core->edge tree
                preds = list(g.predecessors(dev))
                for pred in preds:
                    common_ancestors[pred] = common_ancestors.get(pred, 0) + 1
                    if common_ancestors[pred] > max_shared_count:
                        max_shared_count = common_ancestors[pred]
                        shared_uplink_node = pred

        # If a single node is shared by multiple degraded devices
        if shared_uplink_node and max_shared_count >= 2:
            pct_affected = (max_shared_count / len(degraded_devices)) * 100
            evidence_items.append(
                EvidenceItem(
                    metric="shared_upstream_bottleneck",
                    value=max_shared_count,
                    interpretation=(
                        f"{max_shared_count} of {len(degraded_devices)} degraded devices ({pct_affected:.0f}%) "
                        f"funnel through common upstream node '{shared_uplink_node}'"
                    ),
                    device_id=shared_uplink_node,
                )
            )
            possible_causes.append(
                f"Shared uplink or aggregation bottleneck at {shared_uplink_node} propagating delay/loss downstream"
            )

        # Blast radius analysis: if an interface/node is down, what downstream nodes lose path?
        isolated_nodes: List[str] = []
        for t in telemetry:
            if t.interface_status == "down" and t.device_id in g:
                # Find all nodes that depend downstream on this device
                downstream = nx.descendants(g, t.device_id)
                if downstream:
                    isolated_nodes.extend(list(downstream))
                    evidence_items.append(
                        EvidenceItem(
                            metric="blast_radius_unreachable_nodes",
                            value=len(downstream),
                            interpretation=(
                                f"Interface down on '{t.device_id}' isolates {len(downstream)} "
                                f"downstream devices: {list(downstream)[:5]}"
                            ),
                            device_id=t.device_id,
                        )
                    )
                    possible_causes.append(f"Hard disconnect at {t.device_id} severing downstream access")

        if isolated_nodes:
            severity = SeverityLevel.CRITICAL
            finding = (
                f"Severe topology partition: down link on {degraded_devices[0] if degraded_devices else 'node'} "
                f"isolates {len(isolated_nodes)} downstream network devices."
            )
            confidence = round(min(0.96, max(0.65, 0.75 + 0.20 * min(1.0, len(isolated_nodes) / 5.0))), 2)
            primary_val = len(isolated_nodes)
            recommended_checks.append("Verify physical link connection and check if STP/OSPF failed over")
        elif shared_uplink_node and max_shared_count >= 3:
            severity = SeverityLevel.HIGH
            finding = (
                f"Topology bottleneck identified: {max_shared_count} affected devices "
                f"converge on shared upstream device '{shared_uplink_node}'."
            )
            ratio = max_shared_count / max(1, len(degraded_devices))
            confidence = round(min(0.94, max(0.60, 0.68 + 0.22 * ratio)), 2)
            primary_val = max_shared_count
            recommended_checks.append(f"Inspect upstream port saturation and aggregate capacity on {shared_uplink_node}")
        elif len(degraded_devices) > 0:
            severity = SeverityLevel.MEDIUM
            finding = (
                f"Localized degradation: {len(degraded_devices)} devices experiencing telemetry anomalies, "
                "no systemic core topology partition detected."
            )
            confidence = round(min(0.82, max(0.50, 0.58 + 0.18 * min(1.0, len(degraded_devices) / 8.0))), 2)
            primary_val = len(degraded_devices)
        else:
            severity = SeverityLevel.LOW
            finding = "Campus topology pathing and reachability fully intact across all monitored segments."
            confidence = 0.94
            primary_val = 0

        return self.create_message(
            session_id=session_id,
            target_agent=AgentRole.ORCHESTRATOR,
            message_type=MessageType.DIAGNOSTIC_FINDING,
            finding=finding,
            severity=severity,
            device_ids=[shared_uplink_node] if shared_uplink_node else degraded_devices,
            metric="affected_topology_nodes",
            value=primary_val,
            unit="devices",
            evidence=evidence_items,
            confidence=confidence,
            possible_causes=list(set(possible_causes)),
            recommended_checks=recommended_checks,
            metadata={
                "degraded_devices_count": len(degraded_devices),
                "shared_uplink_node": shared_uplink_node,
                "shared_count": max_shared_count,
                "isolated_nodes_count": len(isolated_nodes),
            },
        )

    async def handle_clarification_request(
        self,
        request: AgentMessage,
        telemetry: List[DeviceTelemetry],
        topology: Optional[CampusTopology],
    ) -> AgentMessage:
        """Handle dynamic clarification queries from the Correlation Agent."""
        if not topology:
            return self.create_message(
                session_id=request.session_id,
                target_agent=request.source_agent,
                message_type=MessageType.CLARIFICATION_RESPONSE,
                finding="Topology data not available for path verification.",
                confidence=0.2,
                in_reply_to=request.message_id,
            )

        g = self._build_graph(topology)
        target_devices = request.device_ids
        suspected_bottleneck = request.metadata.get("suspected_bottleneck")

        # Check if target devices route through suspected_bottleneck
        shared_count = 0
        total_queried = len(target_devices)
        confirmed_nodes = []

        if suspected_bottleneck and suspected_bottleneck in g:
            for dev in target_devices:
                if dev in g:
                    # Check if path exists from suspected_bottleneck to dev or dev to suspected_bottleneck
                    if nx.has_path(g, suspected_bottleneck, dev) or nx.has_path(g, dev, suspected_bottleneck):
                        shared_count += 1
                        confirmed_nodes.append(dev)

        pct = (shared_count / total_queried * 100) if total_queried > 0 else 0.0

        if shared_count > 0:
            finding = (
                f"Topology confirmation affirmative: {shared_count} of {total_queried} ({pct:.0f}%) "
                f"affected devices depend directly on common uplink '{suspected_bottleneck}'."
            )
            confidence = round(min(0.96, max(0.60, 0.70 + 0.24 * (pct / 100.0))), 2)
        else:
            finding = (
                f"Topology confirmation negative: affected devices do not share a single common uplink on '{suspected_bottleneck}'."
            )
            confidence = round(min(0.88, max(0.50, 0.65 + 0.20 * (1.0 - (pct / 100.0)))), 2)

        evidence = [
            EvidenceItem(
                metric="shared_dependency_verification",
                value=f"{shared_count}/{total_queried}",
                interpretation=f"{pct:.0f}% of examined endpoints traverse upstream node '{suspected_bottleneck}'",
                device_id=suspected_bottleneck,
            )
        ]

        return self.create_message(
            session_id=request.session_id,
            target_agent=request.source_agent,
            message_type=MessageType.CLARIFICATION_RESPONSE,
            finding=finding,
            severity=SeverityLevel.HIGH if pct >= 80 else SeverityLevel.MEDIUM,
            device_ids=[suspected_bottleneck] if suspected_bottleneck else target_devices,
            metric="shared_dependency_pct",
            value=round(pct, 1),
            unit="%",
            evidence=evidence,
            confidence=confidence,
            in_reply_to=request.message_id,
            metadata={
                "verified_upstream": suspected_bottleneck,
                "confirmed_nodes": confirmed_nodes,
                "shared_percentage": pct,
            },
        )
