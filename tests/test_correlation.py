import pytest
from app.agents.performance_agent import PerformanceAgent
from app.agents.infrastructure_agent import InfrastructureAgent
from app.agents.connectivity_agent import ConnectivityAgent
from app.agents.correlation_agent import CorrelationAgent
from app.models.telemetry import DeviceTelemetry, BaselineMetrics
from app.models.topology import CampusTopology, TopologyNode, TopologyLink


@pytest.fixture
def hackathon_telemetry():
    return [
        DeviceTelemetry(
            device_id="HOSTEL_CORE_SW_01",
            device_type="switch",
            timestamp="2026-10-31T21:00:00Z",
            latency_ms=145.0,
            jitter_ms=38.0,
            packet_loss_pct=8.2,
            throughput_mbps=9600.0,
            bandwidth_capacity_mbps=10000.0,
            link_utilization_pct=96.0,
            cpu_utilization_pct=62.0,
            memory_utilization_pct=58.0,
            interface_status="up",
            queue_drops=14230,
            crc_errors=4,
            baseline=BaselineMetrics(
                baseline_latency_ms=12.0,
                baseline_link_utilization_pct=42.0,
                baseline_queue_drops=0,
            ),
        ),
        DeviceTelemetry(
            device_id="HOSTEL_ACC_SW_01",
            device_type="switch",
            timestamp="2026-10-31T21:00:00Z",
            latency_ms=146.0,
            jitter_ms=38.5,
            packet_loss_pct=8.2,
            throughput_mbps=820.0,
            bandwidth_capacity_mbps=1000.0,
            link_utilization_pct=82.0,
            cpu_utilization_pct=34.0,
            memory_utilization_pct=42.0,
            interface_status="up",
            queue_drops=820,
            crc_errors=0,
        ),
    ]


@pytest.fixture
def campus_topology():
    return CampusTopology(
        nodes=[
            TopologyNode(node_id="CORE", name="Core Router", node_type="router", segment="BACKBONE"),
            TopologyNode(node_id="HOSTEL_CORE_SW_01", name="Hostel Core", node_type="switch", segment="HOSTEL"),
            TopologyNode(node_id="HOSTEL_ACC_SW_01", name="Hostel Acc", node_type="switch", segment="HOSTEL"),
        ],
        links=[
            TopologyLink(link_id="L1", source_node="CORE", target_node="HOSTEL_CORE_SW_01", is_uplink=True),
            TopologyLink(link_id="L2", source_node="HOSTEL_CORE_SW_01", target_node="HOSTEL_ACC_SW_01", is_uplink=False),
        ],
    )


@pytest.mark.asyncio
async def test_multi_agent_collaboration_proof_remove_agent_changes_diagnosis(
    hackathon_telemetry, campus_topology
):
    """MANDATORY PROOF TEST:

    Verify that the Correlation Agent changes its output based on what findings it receives.
    When an agent's findings are removed, confidence or diagnosis must visibly change.
    """
    perf_agent = PerformanceAgent()
    infra_agent = InfrastructureAgent()
    conn_agent = ConnectivityAgent()
    corr_agent = CorrelationAgent()

    sid = "DX-2026-TEST"

    # Step 1: Collect findings from all 3 domain agents
    perf_finding = await perf_agent.analyze(sid, hackathon_telemetry, campus_topology)
    infra_finding = await infra_agent.analyze(sid, hackathon_telemetry, campus_topology)
    conn_finding = await conn_agent.analyze(sid, hackathon_telemetry, campus_topology)

    all_findings = [perf_finding, infra_finding, conn_finding]

    # Baseline diagnosis with ALL agents present
    diag_full, _, _ = await corr_agent.correlate(
        session_id=sid,
        findings=all_findings,
        telemetry=hackathon_telemetry,
        topology=campus_topology,
        connectivity_agent_handler=conn_agent.handle_clarification_request,
    )
    full_confidence = diag_full.confidence
    assert full_confidence >= 0.85

    # Step 2: REMOVE Infrastructure Agent findings (queue drops 14,230 omitted)
    partial_findings = [perf_finding, conn_finding]
    diag_degraded, _, _ = await corr_agent.correlate(
        session_id=sid,
        findings=partial_findings,
        telemetry=hackathon_telemetry,
        topology=campus_topology,
        connectivity_agent_handler=conn_agent.handle_clarification_request,
        degraded_agents=["infrastructure_agent"],
    )
    degraded_confidence = diag_degraded.confidence

    # PROOF: Confidence must visibly drop when infrastructure agent is missing
    assert degraded_confidence < full_confidence
    assert full_confidence - degraded_confidence >= 0.10
    assert any("infrastructure_agent" in lim for lim in diag_degraded.metadata["limitations"])
