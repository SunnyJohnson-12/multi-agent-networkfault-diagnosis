from typing import Dict, Any, List, Optional, Set
from pydantic import ValidationError
from app.models.telemetry import DeviceTelemetry, TelemetryBatch
from app.models.topology import CampusTopology
from app.models.messages import AgentMessage, AgentRole, MessageType


class ValidationErrorResponse(Exception):
    def __init__(self, error_code: str, message: str, field: Optional[str] = None):
        self.error_code = error_code
        self.message = message
        self.field = field
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.field:
            result["field"] = self.field
        return result


import math
import re

MAX_IDENTIFIER_LENGTH = 128
MAX_TELEMETRY_BATCH_SIZE = 500
MAX_TOPOLOGY_NODES = 500
MAX_TOPOLOGY_LINKS = 1000

SAFE_IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.:]+$")


def validate_telemetry_item(data: Dict[str, Any], require_mandatory: bool = True) -> DeviceTelemetry:
    """Validate a single device telemetry record against domain, finite, and range rules."""
    if not isinstance(data, dict):
        raise ValidationErrorResponse(
            error_code="INVALID_TELEMETRY",
            message="Telemetry record must be a JSON object",
            field="telemetry",
        )

    device_id = data.get("device_id")
    if not device_id or not isinstance(device_id, str) or not device_id.strip():
        raise ValidationErrorResponse(
            error_code="INVALID_DEVICE_ID",
            message="device_id is required and must be a non-empty string",
            field="device_id",
        )
    if len(device_id) > MAX_IDENTIFIER_LENGTH:
        raise ValidationErrorResponse(
            error_code="INVALID_DEVICE_ID",
            message=f"device_id length exceeds maximum allowed ({MAX_IDENTIFIER_LENGTH} chars)",
            field="device_id",
        )
    if not SAFE_IDENTIFIER_REGEX.match(device_id.strip()):
        raise ValidationErrorResponse(
            error_code="INVALID_DEVICE_ID",
            message="device_id contains illegal characters; must be alphanumeric, hyphen, underscore, colon",
            field="device_id",
        )

    # Alias packet_loss to packet_loss_pct if passed
    if "packet_loss" in data and "packet_loss_pct" not in data:
        data["packet_loss_pct"] = data["packet_loss"]

    # Check mandatory fields existence
    if require_mandatory:
        mandatory_fields = ["packet_loss_pct", "link_utilization_pct", "latency_ms"]
        for req_field in mandatory_fields:
            if req_field not in data or data[req_field] is None:
                raise ValidationErrorResponse(
                    error_code="MISSING_FIELD",
                    message=f"Missing required telemetry field: '{req_field}'",
                    field=req_field,
                )

    # Check finite and numeric bounds explicitly
    numeric_checks = [
        ("packet_loss_pct", 0.0, 100.0, "packet_loss_pct must be a finite percentage between 0 and 100"),
        ("link_utilization_pct", 0.0, 100.0, "link_utilization_pct must be a finite percentage between 0 and 100"),
        ("cpu_utilization_pct", 0.0, 100.0, "cpu_utilization_pct must be a finite percentage between 0 and 100"),
        ("memory_utilization_pct", 0.0, 100.0, "memory_utilization_pct must be a finite percentage between 0 and 100"),
    ]

    for field, min_val, max_val, err_msg in numeric_checks:
        val = data.get(field)
        if val is not None:
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ValidationErrorResponse(
                    error_code="INVALID_TYPE",
                    message=f"{field} must be a valid number, got '{val}'",
                    field=field,
                )
            if math.isnan(val) or math.isinf(val):
                raise ValidationErrorResponse(
                    error_code="INVALID_TELEMETRY",
                    message=f"{field} must be a valid finite number",
                    field=field,
                )
            if val < min_val or val > max_val:
                raise ValidationErrorResponse(
                    error_code="INVALID_TELEMETRY",
                    message=f"{field} must be between {min_val} and {max_val}, got {val}",
                    field=field,
                )

    non_negative_checks = [
        ("latency_ms", "latency_ms must be a non-negative finite number"),
        ("jitter_ms", "jitter_ms must be a non-negative finite number"),
        ("throughput_mbps", "throughput_mbps must be a non-negative finite number"),
        ("queue_drops", "queue_drops must be a non-negative integer"),
        ("crc_errors", "crc_errors must be a non-negative integer"),
    ]

    for field, err_msg in non_negative_checks:
        val = data.get(field)
        if val is not None:
            if not isinstance(val, (int, float)) or isinstance(val, bool) or math.isnan(val) or math.isinf(val) or val < 0:
                raise ValidationErrorResponse(
                    error_code="INVALID_TYPE" if isinstance(val, str) else "INVALID_TELEMETRY",
                    message=f"{field} must be a non-negative finite number",
                    field=field,
                )
            if field in ("queue_drops", "crc_errors") and (not isinstance(val, int) or isinstance(val, bool)):
                raise ValidationErrorResponse(
                    error_code="INVALID_TELEMETRY",
                    message=f"{field} must be a non-negative integer",
                    field=field,
                )

    # Bandwidth capacity check
    capacity = data.get("bandwidth_capacity_mbps")
    if capacity is not None:
        if not isinstance(capacity, (int, float)) or isinstance(capacity, bool) or math.isnan(capacity) or math.isinf(capacity) or capacity <= 0:
            raise ValidationErrorResponse(
                error_code="INVALID_TELEMETRY",
                message="bandwidth_capacity_mbps must be a strictly positive finite number",
                field="bandwidth_capacity_mbps",
            )

    try:
        return DeviceTelemetry(**data)
    except ValidationError as e:
        first_err = e.errors()[0]
        field_name = str(first_err["loc"][-1]) if first_err["loc"] else "telemetry"
        raise ValidationErrorResponse(
            error_code="INVALID_TELEMETRY",
            message=first_err["msg"],
            field=field_name,
        )


def validate_topology(data: Dict[str, Any]) -> CampusTopology:
    """Validate campus topology consistency: node presence, non-empty, link targets, and self-loop checks."""
    if not isinstance(data, dict):
        raise ValidationErrorResponse(
            error_code="INVALID_TOPOLOGY",
            message="Topology must be a JSON object",
            field="topology",
        )

    nodes = data.get("nodes")
    if not isinstance(nodes, list) or len(nodes) == 0:
        raise ValidationErrorResponse(
            error_code="EMPTY_TOPOLOGY",
            message="Topology must contain at least one node in 'nodes'",
            field="nodes",
        )
    if len(nodes) > MAX_TOPOLOGY_NODES:
        raise ValidationErrorResponse(
            error_code="INVALID_TOPOLOGY",
            message=f"Topology node count exceeds limit ({MAX_TOPOLOGY_NODES})",
            field="nodes",
        )

    links = data.get("links", [])
    if not isinstance(links, list):
        raise ValidationErrorResponse(
            error_code="INVALID_TOPOLOGY",
            message="'links' must be a list of link objects",
            field="links",
        )
    if len(links) > MAX_TOPOLOGY_LINKS:
        raise ValidationErrorResponse(
            error_code="INVALID_TOPOLOGY",
            message=f"Topology link count exceeds limit ({MAX_TOPOLOGY_LINKS})",
            field="links",
        )

    node_ids: Set[str] = set()
    for idx, node in enumerate(nodes):
        if not isinstance(node, dict) or "node_id" not in node:
            raise ValidationErrorResponse(
                error_code="INVALID_TOPOLOGY_NODE",
                message=f"Node at index {idx} must be an object with 'node_id'",
                field=f"nodes[{idx}]",
            )
        nid = node["node_id"]
        if not isinstance(nid, str) or len(nid) > MAX_IDENTIFIER_LENGTH:
            raise ValidationErrorResponse(
                error_code="INVALID_TOPOLOGY_NODE",
                message=f"Node at index {idx} has invalid node_id length",
                field=f"nodes[{idx}]",
            )
        if nid in node_ids:
            raise ValidationErrorResponse(
                error_code="DUPLICATE_NODE_ID",
                message=f"Duplicate node_id '{nid}' detected in topology",
                field="nodes",
            )
        node_ids.add(nid)

    # Verify link endpoints exist in node_ids and reject self-loops
    for idx, link in enumerate(links):
        if not isinstance(link, dict):
            raise ValidationErrorResponse(
                error_code="INVALID_TOPOLOGY_LINK",
                message=f"Link at index {idx} must be an object",
                field=f"links[{idx}]",
            )
        src = link.get("source_node")
        tgt = link.get("target_node")
        if not src or src not in node_ids:
            raise ValidationErrorResponse(
                error_code="ORPHAN_LINK_ENDPOINT",
                message=f"Link '{link.get('link_id', idx)}' references unknown source_node '{src}'",
                field="links",
            )
        if not tgt or tgt not in node_ids:
            raise ValidationErrorResponse(
                error_code="ORPHAN_LINK_ENDPOINT",
                message=f"Link '{link.get('link_id', idx)}' references unknown target_node '{tgt}'",
                field="links",
            )
        if src == tgt:
            raise ValidationErrorResponse(
                error_code="INVALID_TOPOLOGY_LINK",
                message=f"Link '{link.get('link_id', idx)}' forms a self-loop (source_node '{src}' equals target_node)",
                field="links",
            )

    try:
        return CampusTopology(**data)
    except ValidationError as e:
        first_err = e.errors()[0]
        field_name = str(first_err["loc"][-1]) if first_err["loc"] else "topology"
        raise ValidationErrorResponse(
            error_code="INVALID_TOPOLOGY",
            message=first_err["msg"],
            field=field_name,
        )


def validate_agent_message(data: Dict[str, Any], seen_message_ids: Optional[Set[str]] = None) -> AgentMessage:
    """Validate an incoming agent protocol message."""
    if not isinstance(data, dict):
        raise ValidationErrorResponse(
            error_code="MALFORMED_MESSAGE",
            message="Message must be a valid JSON object",
        )

    # Schema version
    version = data.get("schema_version")
    if version != "1.0":
        raise ValidationErrorResponse(
            error_code="UNSUPPORTED_SCHEMA_VERSION",
            message=f"Unsupported schema_version '{version}'. Expected '1.0'",
            field="schema_version",
        )

    # Message ID and duplicate check
    msg_id = data.get("message_id")
    if not msg_id or not isinstance(msg_id, str):
        raise ValidationErrorResponse(
            error_code="INVALID_MESSAGE_ID",
            message="message_id is required and must be a string",
            field="message_id",
        )
    if seen_message_ids is not None:
        if msg_id in seen_message_ids:
            raise ValidationErrorResponse(
                error_code="DUPLICATE_MESSAGE_ID",
                message=f"Duplicate message_id detected: '{msg_id}'",
                field="message_id",
            )

    # Allowed agents
    valid_agents = {a.value for a in AgentRole}
    src = data.get("source_agent")
    if src not in valid_agents:
        raise ValidationErrorResponse(
            error_code="UNKNOWN_AGENT",
            message=f"Unknown source_agent '{src}'. Must be one of {sorted(list(valid_agents))}",
            field="source_agent",
        )
    tgt = data.get("target_agent")
    if tgt not in valid_agents:
        raise ValidationErrorResponse(
            error_code="UNKNOWN_AGENT",
            message=f"Unknown target_agent '{tgt}'. Must be one of {sorted(list(valid_agents))}",
            field="target_agent",
        )

    # Message type
    valid_types = {t.value for t in MessageType}
    mtype = data.get("message_type")
    if mtype not in valid_types:
        raise ValidationErrorResponse(
            error_code="UNKNOWN_MESSAGE_TYPE",
            message=f"Unknown message_type '{mtype}'. Must be one of {sorted(list(valid_types))}",
            field="message_type",
        )

    # Unit validation
    unit = data.get("unit")
    if unit is not None and str(unit).strip() != "":
        clean_unit = str(unit).strip().lower()
        if clean_unit not in AgentMessage.ALLOWED_UNITS:
            raise ValidationErrorResponse(
                error_code="INVALID_UNIT",
                message=f"Invalid unit '{unit}'. Allowed network units: {sorted(list(AgentMessage.ALLOWED_UNITS))}",
                field="unit",
            )

    try:
        return AgentMessage(**data)
    except ValidationError as e:
        first_err = e.errors()[0]
        field_name = str(first_err["loc"][-1]) if first_err["loc"] else "message"
        err_type = first_err.get("type", "")
        code = "INVALID_TYPE" if "type" in err_type or "parsing" in err_type else "INVALID_MESSAGE_PAYLOAD"
        if field_name == "unit":
            code = "INVALID_UNIT"
        raise ValidationErrorResponse(
            error_code=code,
            message=first_err["msg"],
            field=field_name,
        )

