import pytest
import asyncio
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.models.messages import AgentMessage, AgentRole, MessageType, SeverityLevel
from app.models.diagnosis import DiagnosisStatus
from app.models.telemetry import DeviceTelemetry
from app.validation.validators import (
    validate_telemetry_item,
    validate_agent_message,
    ValidationErrorResponse,
)
from app.orchestration.orchestrator import orchestrator
from app.orchestration.message_bus import MessageBus
from app.services.session_store import session_store
from app.services.hypothesis_scoring import HypothesisScoringEngine


@pytest.fixture
def client():
    return TestClient(app)


# -----------------------------------------------------------------------------
# 1. PROMPT #11: VALIDATION & BAD INPUT TESTS (CASES 1-6)
# -----------------------------------------------------------------------------

def test_validation_case_1_missing_field():
    """Case 1 — Missing field: Remove packet_loss. Expected: validation failure with clear message."""
    bad_data = {
        "device_id": "SWITCH_01",
        "device_type": "switch",
        "timestamp": "2026-11-01T00:00:00Z",
        "link_utilization_pct": 50.0,
        "latency_ms": 10.0,
        # packet_loss omitted
    }
    with pytest.raises(ValidationErrorResponse) as exc_info:
        validate_telemetry_item(bad_data, require_mandatory=True)
    assert exc_info.value.error_code == "MISSING_FIELD"
    assert "packet_loss_pct" in exc_info.value.message


def test_validation_case_2_wrong_type():
    """Case 2 — Wrong type: Example: packet_loss = 'high'. Expected: validation error."""
    bad_data = {
        "device_id": "SWITCH_01",
        "device_type": "switch",
        "timestamp": "2026-11-01T00:00:00Z",
        "link_utilization_pct": 50.0,
        "latency_ms": 10.0,
        "packet_loss": "high",  # String instead of numeric float
    }
    with pytest.raises(ValidationErrorResponse) as exc_info:
        validate_telemetry_item(bad_data)
    assert exc_info.value.error_code == "INVALID_TYPE"
    assert "packet_loss_pct" in exc_info.value.message


def test_validation_case_3_invalid_unit():
    """Case 3 — Invalid unit: Example: latency = 145, unit = 'kg'. Expected: unit validation failure."""
    bad_msg = {
        "message_id": "msg-unit-test-01",
        "session_id": "DX-2026-TEST",
        "timestamp": "2026-11-01T00:00:00Z",
        "source_agent": "performance_agent",
        "target_agent": "correlation_agent",
        "message_type": "diagnostic_finding",
        "schema_version": "1.0",
        "metric": "latency",
        "value": 145.0,
        "unit": "kg",  # Invalid unit for network latency
        "finding": "High latency detected",
        "severity": "medium",
    }
    with pytest.raises(ValidationErrorResponse) as exc_info:
        validate_agent_message(bad_msg)
    assert exc_info.value.error_code == "INVALID_UNIT"
    assert "kg" in exc_info.value.message


def test_validation_case_4_unsupported_schema():
    """Case 4 — Unsupported schema: Example: schema_version = '99.0'. Expected: clear rejection."""
    bad_msg = {
        "message_id": "msg-schema-test-01",
        "session_id": "DX-2026-TEST",
        "timestamp": "2026-11-01T00:00:00Z",
        "source_agent": "performance_agent",
        "target_agent": "correlation_agent",
        "message_type": "diagnostic_finding",
        "schema_version": "99.0",  # Unsupported version
        "finding": "Test message",
        "severity": "low",
    }
    with pytest.raises(ValidationErrorResponse) as exc_info:
        validate_agent_message(bad_msg)
    assert exc_info.value.error_code == "UNSUPPORTED_SCHEMA_VERSION"
    assert "99.0" in exc_info.value.message


def test_validation_case_5_unknown_agent():
    """Case 5 — Unknown agent: Example: source_agent = 'UnknownAgent'. Expected: message rejected safely."""
    bad_msg = {
        "message_id": "msg-agent-test-01",
        "session_id": "DX-2026-TEST",
        "timestamp": "2026-11-01T00:00:00Z",
        "source_agent": "UnknownAgent",  # Unknown agent role
        "target_agent": "correlation_agent",
        "message_type": "diagnostic_finding",
        "schema_version": "1.0",
        "finding": "Test message",
        "severity": "low",
    }
    with pytest.raises(ValidationErrorResponse) as exc_info:
        validate_agent_message(bad_msg)
    assert exc_info.value.error_code in ("UNKNOWN_AGENT", "UNKNOWN_AGENT_ROLE")
    assert "UnknownAgent" in exc_info.value.message


@pytest.mark.asyncio
async def test_validation_case_6_duplicate_message():
    """Case 6 — Duplicate message: Send same message_id twice. Expected: duplicate handled safely without corrupting diagnosis."""
    bus = MessageBus(session_id="DX-TEST-DEDUP")
    msg = AgentMessage(
        message_id="msg-unique-dedup-01",
        session_id="DX-TEST-DEDUP",
        timestamp=datetime.utcnow().isoformat() + "Z",
        source_agent=AgentRole.PERFORMANCE_AGENT,
        target_agent=AgentRole.CORRELATION_AGENT,
        message_type=MessageType.DIAGNOSTIC_FINDING,
        schema_version="1.0",
        finding="Initial performance finding",
        severity=SeverityLevel.MEDIUM,
    )
    first_res = await bus.publish(msg)
    assert first_res is not None

    # Publishing duplicate message with identical ID safely raises DUPLICATE_MESSAGE_ID
    with pytest.raises(ValidationErrorResponse) as exc_info:
        await bus.publish(msg)
    assert exc_info.value.error_code == "DUPLICATE_MESSAGE_ID"

    # Verify bus history length is exactly 1 and is not corrupted
    history = bus.get_messages()
    assert len(history) == 1
    assert history[0].message_id == "msg-unique-dedup-01"


# -----------------------------------------------------------------------------
# 2. PROMPT #9: AMBIGUOUS CASE HANDLING
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ambiguous_conflicting_telemetry():
    """Verify scenario where evidence is conflicting returns status: AMBIGUOUS with required explanation."""
    ambiguous_telemetry = [
        {
            "device_id": "ACAD_DIST_SW_02",
            "device_name": "Academic Block Distribution Switch",
            "device_type": "switch",
            "interface": "TenGig1/1/1",
            "timestamp": "2026-10-31T17:45:00Z",
            "latency_ms": 65.0,
            "jitter_ms": 12.0,
            "packet_loss_pct": 5.4,  # High packet loss
            "throughput_mbps": 480.0,
            "bandwidth_capacity_mbps": 1000.0,
            "link_utilization_pct": 48.0,
            "cpu_utilization_pct": 32.0,  # Normal CPU
            "memory_utilization_pct": 42.0,  # Normal Memory
            "interface_status": "up",
            "queue_drops": 0,  # 0 Queue drops
            "crc_errors": 0,  # 0 CRC errors
        }
    ]

    session = await orchestrator.run_diagnostic_session(
        telemetry_raw=ambiguous_telemetry,
        incident_id="INC-AMBIG-TEST",
    )
    report = session.final_report
    assert report is not None
    assert report.status == DiagnosisStatus.AMBIGUOUS
    assert "Available evidence is insufficient to determine a unique root cause" in " ".join(report.limitations)
    assert report.confidence < 0.70  # Lower confidence due to ambiguity


# -----------------------------------------------------------------------------
# 3. PROMPT #10: INSUFFICIENT DATA CASE HANDLING
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_insufficient_evidence_case():
    """Verify scenario with missing critical telemetry returns status: INSUFFICIENT_EVIDENCE without inventing diagnosis."""
    incomplete_telemetry = [
        {
            "device_id": "HOSTEL_ACCESS_SW_04",
            "device_name": "Hostel Access Switch 04",
            "device_type": "switch",
            "interface": "GigabitEthernet0/1",
            "timestamp": "2026-10-31T18:00:00Z",
            "interface_status": "up",
            "cpu_utilization_pct": 25.0,
            "memory_utilization_pct": 35.0,
            "queue_drops": 0,
            "crc_errors": 0,
            # packet_loss_pct and link_utilization_pct missing
        }
    ]

    session = await orchestrator.run_diagnostic_session(
        telemetry_raw=incomplete_telemetry,
        incident_id="INC-INSUFFICIENT-TEST",
    )
    report = session.final_report
    assert report is not None
    assert report.status == DiagnosisStatus.INSUFFICIENT_EVIDENCE
    assert "Insufficient telemetry" in report.suspected_root_cause or "Insufficient Telemetry Coverage" in report.suspected_root_cause
    assert report.confidence <= 0.20

    # Verify limitations report missing fields and explanations
    limitations_str = " ".join(report.limitations)
    assert "Missing critical telemetry" in limitations_str
    assert "Why it matters" in limitations_str
    assert "Additional telemetry required" in limitations_str


# -----------------------------------------------------------------------------
# 4. PROMPT #17: NORMAL NETWORK BASELINE OPERATION
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_normal_network_not_flagged_as_fault():
    """Healthy baseline telemetry must produce NO_FAULT / NORMAL without false positive diagnosis."""
    normal_telemetry = [
        {
            "device_id": "CORE_ROUTER_01",
            "device_name": "Campus Core Router 01",
            "device_type": "router",
            "interface": "TenGig0/0/0",
            "timestamp": "2026-10-31T12:00:00Z",
            "latency_ms": 15.0,
            "jitter_ms": 1.2,
            "packet_loss_pct": 0.05,
            "throughput_mbps": 350.0,
            "bandwidth_capacity_mbps": 1000.0,
            "link_utilization_pct": 35.0,
            "cpu_utilization_pct": 28.0,
            "memory_utilization_pct": 36.0,
            "interface_status": "up",
            "queue_drops": 0,
            "crc_errors": 0,
        }
    ]

    session = await orchestrator.run_diagnostic_session(
        telemetry_raw=normal_telemetry,
        incident_id="INC-NORMAL-TEST",
    )
    report = session.final_report
    assert report is not None
    assert report.status == DiagnosisStatus.NO_FAULT_DETECTED
    assert "No significant network fault" in report.suspected_root_cause or "Normal Network Operation" in report.suspected_root_cause
    assert len(report.affected_devices) == 0


# -----------------------------------------------------------------------------
# 5. PROMPT #8: DYNAMIC CONFIDENCE CALCULATION
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_confidence_is_dynamic_not_hardcoded():
    """Verify confidence formula is deterministic and dynamic based on evidence strength and ablation."""
    congestion_telemetry = [
        {
            "device_id": "HOSTEL_CORE_SW_01",
            "device_type": "switch",
            "timestamp": "2026-10-31T12:00:00Z",
            "latency_ms": 145.0,
            "jitter_ms": 38.0,
            "packet_loss_pct": 8.3,
            "link_utilization_pct": 96.0,
            "cpu_utilization_pct": 62.0,
            "memory_utilization_pct": 58.0,
            "interface_status": "up",
            "queue_drops": 15790,
            "crc_errors": 0,
        }
    ]

    # Run with all agents
    full_session = await orchestrator.run_diagnostic_session(
        telemetry_raw=congestion_telemetry,
        disabled_agents=[],
    )
    full_conf = full_session.final_report.confidence

    # Run with Performance Agent disabled
    ablation_session = await orchestrator.run_diagnostic_session(
        telemetry_raw=congestion_telemetry,
        disabled_agents=["performance_agent"],
    )
    ablation_conf = ablation_session.final_report.confidence

    # Confidence must NOT be hardcoded 1.0, and removing performance agent must decrease confidence
    assert 0.0 < full_conf < 1.0
    assert 0.0 < ablation_conf < 1.0
    assert full_conf > ablation_conf
    assert full_session.final_report.status == DiagnosisStatus.DIAGNOSED


# -----------------------------------------------------------------------------
# 6. PROMPT #24: API ENDPOINTS VERIFICATION
# -----------------------------------------------------------------------------

def test_api_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert len(data["active_agents"]) == 5


def test_api_telemetry_post_endpoint(client):
    res = client.post(
        "/api/telemetry",
        json={
            "records": [
                {
                    "device_id": "TEST_SW_01",
                    "device_type": "switch",
                    "timestamp": "2026-11-01T00:00:00Z",
                    "link_utilization_pct": 45.0,
                    "latency_ms": 20.0,
                    "packet_loss": 0.1,
                    "cpu_utilization_pct": 30.0,
                    "memory_utilization_pct": 40.0,
                }
            ]
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["validated"] is True
    assert data["count"] == 1


def test_api_diagnose_and_messages_endpoints(client):
    res = client.post(
        "/api/diagnose",
        json={
            "telemetry": [
                {
                    "device_id": "TEST_SW_02",
                    "device_type": "switch",
                    "timestamp": "2026-11-01T00:00:00Z",
                    "link_utilization_pct": 92.0,
                    "latency_ms": 120.0,
                    "packet_loss": 6.5,
                    "cpu_utilization_pct": 40.0,
                    "memory_utilization_pct": 50.0,
                    "queue_drops": 5000,
                }
            ],
            "incident_id": "INC-API-TEST",
        },
    )
    assert res.status_code == 200
    report = res.json()
    assert report["incident_id"] == "INC-API-TEST"
    assert "suspected_root_cause" in report
    assert "confidence" in report
    assert "severity" in report
    assert "message_ids" in report

    # Test GET /api/messages
    msg_res = client.get("/api/messages")
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert len(msg_data["messages"]) > 0

    # Test GET /api/findings
    findings_res = client.get("/api/findings")
    assert findings_res.status_code == 200
    findings_data = findings_res.json()
    assert len(findings_data["findings"]) > 0

    # Test GET /api/diagnosis/{id}
    diag_res = client.get("/api/diagnosis/INC-API-TEST")
    assert diag_res.status_code == 200
    assert diag_res.json()["incident_id"] == "INC-API-TEST"
