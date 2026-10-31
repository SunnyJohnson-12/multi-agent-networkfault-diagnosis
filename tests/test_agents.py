import pytest
from app.agents.performance_agent import PerformanceAgent
from app.agents.infrastructure_agent import InfrastructureAgent
from app.agents.connectivity_agent import ConnectivityAgent
from app.models.telemetry import DeviceTelemetry, BaselineMetrics
from app.models.topology import CampusTopology, TopologyNode, TopologyLink
from app.models.messages import AgentRole, MessageType, SeverityLevel


@pytest.fixture
def sample_topology():
    return CampusTopology(
        nodes=[
            TopologyNode(node_id="CORE_01", name="Core", node_type="router", segment="BACKBONE"),
            TopologyNode(node_id="SW_01", name="Switch 1", node_type="switch", segment="HOSTEL"),
            TopologyNode(node_id="AP_01", name="AP 1", node_type="access_point", segment="HOSTEL"),
            TopologyNode(node_id="AP_02", name="AP 2", node_type="access_point", segment="HOSTEL"),
        ],
        links=[
            TopologyLink(link_id="L1", source_node="CORE_01", target_node="SW_01", is_uplink=True),
            TopologyLink(link_id="L2", source_node="SW_01", target_node="AP_01", is_uplink=False),
            TopologyLink(link_id="L3", source_node="SW_01", target_node="AP_02", is_uplink=False),
        ],
    )


@pytest.mark.asyncio
async def test_performance_agent_detects_congestion():
    agent = PerformanceAgent()
    telemetry = [
        DeviceTelemetry(
            device_id="SW_01",
            device_type="switch",
            timestamp="2026-10-31T10:00:00Z",
            latency_ms=180.0,
            jitter_ms=35.0,
            packet_loss_pct=6.5,
            throughput_mbps=950.0,
            bandwidth_capacity_mbps=1000.0,
            link_utilization_pct=95.0,
            cpu_utilization_pct=30.0,
            memory_utilization_pct=40.0,
            baseline=BaselineMetrics(baseline_link_utilization_pct=30.0, baseline_latency_ms=10.0),
        )
    ]
    msg = await agent.analyze("DX-2026-0001", telemetry)
    assert msg.source_agent == AgentRole.PERFORMANCE_AGENT
    assert msg.severity == SeverityLevel.CRITICAL
    assert msg.value == 95.0
    assert "Severe link congestion" in msg.finding


@pytest.mark.asyncio
async def test_infrastructure_agent_detects_queue_drops_and_crc():
    agent = InfrastructureAgent()
    telemetry = [
        DeviceTelemetry(
            device_id="SW_01",
            device_type="switch",
            timestamp="2026-10-31T10:00:00Z",
            latency_ms=25.0,
            packet_loss_pct=1.0,
            link_utilization_pct=40.0,
            cpu_utilization_pct=30.0,
            memory_utilization_pct=40.0,
            queue_drops=8500,
            crc_errors=150,
        )
    ]
    msg = await agent.analyze("DX-2026-0001", telemetry)
    assert msg.source_agent == AgentRole.INFRASTRUCTURE_AGENT
    assert msg.metadata["total_queue_drops"] == 8500
    assert msg.metadata["total_crc_errors"] == 150


@pytest.mark.asyncio
async def test_connectivity_agent_shared_bottleneck_and_clarification(sample_topology):
    agent = ConnectivityAgent()
    telemetry = [
        DeviceTelemetry(
            device_id="AP_01",
            device_type="access_point",
            timestamp="2026-10-31T10:00:00Z",
            latency_ms=90.0,
            packet_loss_pct=5.0,
            link_utilization_pct=40.0,
            cpu_utilization_pct=20.0,
            memory_utilization_pct=30.0,
        ),
        DeviceTelemetry(
            device_id="AP_02",
            device_type="access_point",
            timestamp="2026-10-31T10:00:00Z",
            latency_ms=92.0,
            packet_loss_pct=5.2,
            link_utilization_pct=42.0,
            cpu_utilization_pct=21.0,
            memory_utilization_pct=31.0,
        ),
    ]
    msg = await agent.analyze("DX-2026-0001", telemetry, sample_topology)
    assert msg.source_agent == AgentRole.CONNECTIVITY_AGENT
    assert msg.metadata["shared_uplink_node"] == "SW_01"

    # Cross-query clarification
    clarif_req = agent.create_message(
        session_id="DX-2026-0001",
        target_agent=AgentRole.CONNECTIVITY_AGENT,
        message_type=MessageType.CLARIFICATION_REQUEST,
        finding="Verify bottleneck",
        device_ids=["AP_01", "AP_02"],
        metadata={"suspected_bottleneck": "SW_01"},
    )
    resp = await agent.handle_clarification_request(clarif_req, telemetry, sample_topology)
    assert resp.message_type == MessageType.CLARIFICATION_RESPONSE
    assert resp.metadata["shared_percentage"] == 100.0
    assert "Affirmative" in resp.finding or "affirmative" in resp.finding.lower()
