import pytest
from app.validation.validators import (
    validate_telemetry_item,
    validate_topology,
    validate_agent_message,
    ValidationErrorResponse,
)


def test_valid_telemetry():
    raw = {
        "device_id": "HOSTEL_CORE_SW_01",
        "device_type": "switch",
        "timestamp": "2026-10-31T10:00:00Z",
        "latency_ms": 12.5,
        "packet_loss_pct": 0.5,
        "link_utilization_pct": 45.0,
        "cpu_utilization_pct": 30.0,
        "memory_utilization_pct": 40.0,
    }
    model = validate_telemetry_item(raw)
    assert model.device_id == "HOSTEL_CORE_SW_01"
    assert model.link_utilization_pct == 45.0


def test_invalid_telemetry_percentage_bounds():
    # packet_loss_pct > 100
    raw = {
        "device_id": "DEV-01",
        "device_type": "router",
        "timestamp": "2026-10-31T10:00:00Z",
        "latency_ms": 10.0,
        "packet_loss_pct": 105.0,
        "link_utilization_pct": 50.0,
        "cpu_utilization_pct": 20.0,
        "memory_utilization_pct": 30.0,
    }
    with pytest.raises(ValidationErrorResponse) as exc_info:
        validate_telemetry_item(raw)
    assert exc_info.value.error_code == "INVALID_TELEMETRY"
    assert exc_info.value.field == "packet_loss_pct"


def test_invalid_telemetry_negative_latency():
    raw = {
        "device_id": "DEV-01",
        "device_type": "router",
        "timestamp": "2026-10-31T10:00:00Z",
        "latency_ms": -10.0,
        "packet_loss_pct": 5.0,
        "link_utilization_pct": 50.0,
        "cpu_utilization_pct": 20.0,
        "memory_utilization_pct": 30.0,
    }
    with pytest.raises(ValidationErrorResponse) as exc_info:
        validate_telemetry_item(raw)
    assert exc_info.value.error_code == "INVALID_TELEMETRY"
    assert exc_info.value.field == "latency_ms"


def test_missing_device_id():
    raw = {
        "device_type": "router",
        "timestamp": "2026-10-31T10:00:00Z",
        "latency_ms": 10.0,
        "packet_loss_pct": 5.0,
        "link_utilization_pct": 50.0,
        "cpu_utilization_pct": 20.0,
        "memory_utilization_pct": 30.0,
    }
    with pytest.raises(ValidationErrorResponse) as exc_info:
        validate_telemetry_item(raw)
    assert exc_info.value.error_code == "INVALID_DEVICE_ID"


def test_topology_orphan_links():
    raw = {
        "nodes": [
            {"node_id": "NODE_A", "name": "Node A", "node_type": "switch", "segment": "HOSTEL"}
        ],
        "links": [
            {
                "link_id": "LNK-01",
                "source_node": "NODE_A",
                "target_node": "NODE_NON_EXISTENT",
                "bandwidth_mbps": 1000.0,
            }
        ],
    }
    with pytest.raises(ValidationErrorResponse) as exc_info:
        validate_topology(raw)
    assert exc_info.value.error_code == "ORPHAN_LINK_ENDPOINT"


def test_agent_message_protocol_validation():
    valid_msg = {
        "message_id": "msg-1234",
        "session_id": "DX-2026-0001",
        "timestamp": "2026-10-31T10:00:00Z",
        "source_agent": "performance_agent",
        "target_agent": "orchestrator",
        "message_type": "diagnostic_finding",
        "schema_version": "1.0",
        "finding": "Link saturation detected",
        "severity": "high",
        "confidence": 0.9,
    }
    msg_model = validate_agent_message(valid_msg)
    assert msg_model.source_agent.value == "performance_agent"

    # Unsupported schema version
    bad_ver = dict(valid_msg, schema_version="2.0", message_id="msg-999")
    with pytest.raises(ValidationErrorResponse) as exc_info:
        validate_agent_message(bad_ver)
    assert exc_info.value.error_code == "UNSUPPORTED_SCHEMA_VERSION"

    # Unknown agent
    bad_agent = dict(valid_msg, source_agent="rogue_agent", message_id="msg-888")
    with pytest.raises(ValidationErrorResponse) as exc_info:
        validate_agent_message(bad_agent)
    assert exc_info.value.error_code == "UNKNOWN_AGENT"

    # Duplicate message ID
    seen = {"msg-1234"}
    with pytest.raises(ValidationErrorResponse) as exc_info:
        validate_agent_message(valid_msg, seen_message_ids=seen)
    assert exc_info.value.error_code == "DUPLICATE_MESSAGE_ID"
