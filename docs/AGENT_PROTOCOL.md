# Inter-Agent Diagnostic Message Protocol (IADMP)
**Protocol Specification — Version 1.0**

---

## 1. Overview & Purpose
The Inter-Agent Diagnostic Message Protocol (IADMP) defines the standardized, versioned JSON schema governing all data exchange and diagnostic coordination between autonomous agents in **The Signal Room**.

No agent in the system shares unvalidated state. Every communication hop—from initial task dispatch to domain telemetry findings, cross-agent clarification queries, and the consolidated root-cause diagnosis—must be encapsulated in an immutable, validated message envelope.

---

## 2. Standardized Message Envelope

```json
{
  "message_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "session_id": "DX-2026-0001",
  "timestamp": "2026-10-31T21:00:02Z",
  "source_agent": "performance_agent",
  "target_agent": "orchestrator",
  "message_type": "diagnostic_finding",
  "schema_version": "1.0",
  "device_ids": ["HOSTEL_CORE_SW_01"],
  "metric": "link_utilization_pct",
  "value": 96.0,
  "unit": "%",
  "severity": "critical",
  "finding": "Severe link congestion detected on HOSTEL_CORE_SW_01 uplink with 96.0% utilization, 8.2% packet loss, and latency spike to 145.0 ms.",
  "evidence": [
    {
      "metric": "link_utilization_pct",
      "value": 96.0,
      "interpretation": "Critical link saturation (96.0% >= 90% threshold), baseline was 42.0%",
      "baseline": 42.0,
      "device_id": "HOSTEL_CORE_SW_01"
    }
  ],
  "confidence": 0.92,
  "possible_causes": [
    "Excessive network traffic saturating physical uplink capacity",
    "Buffer tail drop causing packet loss"
  ],
  "recommended_checks": [
    "Inspect top talkers and per-flow bandwidth consumption via NetFlow/IPFIX",
    "Verify QoS queue allocations and egress rate-limiters"
  ],
  "in_reply_to": null,
  "metadata": {
    "max_latency_ms": 145.0,
    "max_loss_pct": 8.2,
    "max_jitter_ms": 38.0,
    "analyzed_records_count": 12
  }
}
```

---

## 3. Comprehensive Field Specification

| Field | Type | Allowed Values | Units | Producer Agents | Consumer Agents | Description |
|---|---|---|---|---|---|---|
| `message_id` | `string (UUIDv4)` | Valid UUID string | N/A | All agents | Orchestrator, All | Globally unique identifier for message deduplication and traceability. |
| `session_id` | `string` | Regex: `^DX-\d{4}-\d{4}$` | N/A | Orchestrator | All agents | Diagnostic investigation session identifier. |
| `timestamp` | `string (ISO-8601)` | Valid UTC ISO-8601 string | N/A | All agents | All agents | Exact generation timestamp in UTC (`YYYY-MM-DDTHH:MM:SSZ`). |
| `source_agent` | `string (Enum)` | `orchestrator`, `performance_agent`, `infrastructure_agent`, `connectivity_agent`, `correlation_agent`, `reporting_agent` | N/A | Origin agent | Recipient | Identity of transmitting agent. Unknown agents are strictly rejected. |
| `target_agent` | `string (Enum)` | `orchestrator`, `performance_agent`, `infrastructure_agent`, `connectivity_agent`, `correlation_agent`, `reporting_agent`, `broadcast` | N/A | Origin agent | Message Bus | Intended recipient or `broadcast` for domain fanout. |
| `message_type` | `string (Enum)` | `task_dispatch`, `diagnostic_finding`, `findings_bundle`, `clarification_request`, `clarification_response`, `consolidated_diagnosis`, `final_report`, `agent_error` | N/A | All agents | All agents | Protocol message type governing schema validation and routing. |
| `schema_version` | `string` | `"1.0"` | N/A | All agents | All agents | Must be `"1.0"`. Any other version is rejected with `UNSUPPORTED_SCHEMA_VERSION`. |
| `device_ids` | `array[string]` | Non-empty device strings | N/A | All agents | All agents | Network device identifiers directly involved in this message finding. |
| `metric` | `string` | E.g., `link_utilization_pct`, `queue_drops`, `crc_errors`, `cpu_utilization_pct`, `latency_ms` | N/A | Domain agents | Correlation Agent | Primary metric evaluated by the agent. |
| `value` | `number \| string \| bool \| null` | Range-dependent (0-100 for %, >=0 for ms/drops) | Matches `unit` | Domain agents | Correlation Agent | Scalar or summary value of the primary metric. |
| `unit` | `string` | `"%"` , `"ms"` , `"drops"` , `"errors"` , `"devices"` , `"ratio"` | N/A | Domain agents | Reporting Agent | Unit of measurement for metric value. |
| `severity` | `string (Enum)` | `low`, `medium`, `high`, `critical` | N/A | All agents | Orchestrator, Correlation | Agent severity classification based on threshold deviation. |
| `finding` | `string` | Non-empty human readable string | N/A | All agents | All agents | Synthesized finding summary in clear engineering terms. |
| `evidence` | `array[object]` | List of `{metric, value, interpretation, baseline, device_id}` | N/A | Domain agents | Correlation, Reporting | Concrete, atomic telemetry proofs supporting the finding. |
| `confidence` | `number` | Float in range `[0.0, 1.0]` | Ratio | All agents | Correlation, Reporting | Localized agent certainty level. |
| `possible_causes`| `array[string]` | Candidate cause explanations | N/A | Domain agents | Correlation Agent | Agent-proposed candidate root causes. |
| `recommended_checks`| `array[string]` | Actionable verification steps | N/A | Domain agents, Correlation | Operational checks suggested for network engineers. |
| `in_reply_to` | `string \| null` | UUID of referenced message | N/A | Correlation, Connectivity | Correlation, Orchestrator | Foreign message ID linking request-response dialogues. |
| `metadata` | `object` | Arbitrary JSON key-value map | N/A | All agents | All agents | Auxiliary diagnostic analytics (e.g. queue counters, blast radius). |

---

## 4. Message Types & Lifecycle Transitions

```
+-------------------------------------------------------------------------+
|                              ORCHESTRATOR                               |
+----+-----------------------------+---------------------------------+----+
     |                             |                                 |
     | task_dispatch               | task_dispatch                   | task_dispatch
     v                             v                                 v
+----+-------------+         +-----+----------------+         +------+-------------+
| Performance Agent|         | Infrastructure Agent |         | Connectivity Agent |
+----+-------------+         +-----+----------------+         +------+-------------+
     |                             |                                 |
     | diagnostic_finding          | diagnostic_finding              | diagnostic_finding
     +-----------------------------+---------------------------------+
                                   |
                                   v
                             +-----+--------------+
                             |    findings_bundle |
                             +-----+--------------+
                                   |
                                   v
                             +-----+--------------+
                             |  Correlation Agent |<--+
                             +-----+--------------+   |
                                   |                  | clarification_response
                                   | clarification_   |
                                   | request          |
                                   v                  |
                             +-----+--------------+   |
                             | Connectivity Agent +---+
                             +--------------------+
                                   |
                                   | consolidated_diagnosis
                                   v
                             +-----+--------------+
                             |  Reporting Agent   |
                             +-----+--------------+
                                   |
                                   | final_report
                                   v
                             +-----+--------------+
                             |    ORCHESTRATOR    |
                             +--------------------+
```

---

## 5. Error Protocol & Validation Rejection Codes

When invalid, malformed, or out-of-spec messages arrive, the system immediately rejects the payload with an explicit `ValidationErrorResponse` JSON object:

```json
{
  "error": true,
  "error_code": "UNSUPPORTED_SCHEMA_VERSION",
  "message": "Unsupported schema_version '2.0'. Expected '1.0'",
  "field": "schema_version"
}
```

Standard Error Codes:
- `MALFORMED_MESSAGE`: Payload is not a valid JSON object.
- `UNSUPPORTED_SCHEMA_VERSION`: `schema_version` != `"1.0"`.
- `INVALID_MESSAGE_ID`: Message ID is empty, missing, or malformed.
- `DUPLICATE_MESSAGE_ID`: Message ID has already been recorded on the session bus.
- `UNKNOWN_AGENT`: `source_agent` or `target_agent` is not registered in `AgentRole`.
- `UNKNOWN_MESSAGE_TYPE`: `message_type` is not registered in `MessageType`.
- `INVALID_UNIT`: Metric unit is not in allowed set (`%`, `ms`, `drops`, `errors`, `devices`, `ratio`, `mbps`, `celsius`, `count`). E.g. `latency = 145, unit = "kg"` is rejected.
- `INVALID_TYPE`: Metric value has an illegal data type (e.g. `packet_loss = "high"` string instead of float).
- `MISSING_FIELD`: Telemetry item lacks required metric keys.
- `INVALID_TELEMETRY`: Numeric values violate bounds (e.g., negative latency, percentage > 100).
- `ORPHAN_LINK_ENDPOINT`: Topology link references an unknown device ID.

---

## 6. Example Agent-to-Agent Clarification Dialogue

During complex or multi-device congestion, the Correlation Agent actively queries the Connectivity Agent to resolve topology dependencies.

### Step 1: Correlation Agent Request
```json
{
  "message_id": "req-7f8e-4a91-92b0-8c2919ab5610",
  "session_id": "DX-2026-0001",
  "timestamp": "2026-10-31T21:00:03Z",
  "source_agent": "correlation_agent",
  "target_agent": "connectivity_agent",
  "message_type": "clarification_request",
  "schema_version": "1.0",
  "device_ids": [
    "HOSTEL_ACC_SW_01",
    "HOSTEL_ACC_SW_02",
    "HOSTEL_ACC_SW_03"
  ],
  "metric": "shared_uplink_dependency",
  "value": 3,
  "unit": "devices",
  "severity": "medium",
  "finding": "Inquiry: Confirm whether affected devices share a common upstream bottleneck switch.",
  "evidence": [],
  "confidence": 0.50,
  "in_reply_to": null,
  "metadata": {
    "query": "shared_upstream_dependency",
    "suspected_node": "HOSTEL_CORE_SW_01"
  }
}
```

### Step 2: Connectivity Agent Response
```json
{
  "message_id": "resp-8a12-4c33-b1d8-7e3909ef2244",
  "session_id": "DX-2026-0001",
  "timestamp": "2026-10-31T21:00:04Z",
  "source_agent": "connectivity_agent",
  "target_agent": "correlation_agent",
  "message_type": "clarification_response",
  "schema_version": "1.0",
  "device_ids": [
    "HOSTEL_ACC_SW_01",
    "HOSTEL_ACC_SW_02",
    "HOSTEL_ACC_SW_03"
  ],
  "metric": "upstream_bottleneck_convergence",
  "value": 100.0,
  "unit": "%",
  "severity": "high",
  "finding": "Topology graph verified: 100.0% of affected hostel access switches (3/3) route through upstream aggregation switch 'HOSTEL_CORE_SW_01'.",
  "evidence": [
    {
      "metric": "shared_uplink_convergence_pct",
      "value": 100.0,
      "interpretation": "100.0% of affected hostel access switches converge on HOSTEL_CORE_SW_01",
      "device_id": "HOSTEL_CORE_SW_01"
    }
  ],
  "confidence": 0.95,
  "in_reply_to": "req-7f8e-4a91-92b0-8c2919ab5610",
  "metadata": {
    "verified_upstream": "HOSTEL_CORE_SW_01",
    "shared_percentage": 100.0
  }
}
```

---

## 7. Confidence & Severity Semantics

### Confidence Semantics (`[0.0, 1.0]`)
- **0.90 – 0.96 (High / Converged)**: Multi-agent consensus confirmed across performance, infrastructure, and topology planes.
- **0.70 – 0.89 (Moderate)**: Corroborated by 2 domains, or 1 domain degraded.
- **0.35 – 0.50 (Ambiguous)**: Conflicting telemetry signals present (e.g. packet loss without buffer drops).
- **0.15 (Insufficient)**: Essential telemetry missing from data stream.

### Severity Semantics
- **`critical`**: Service-severing fault (e.g. interface physically down, packet loss > 10%).
- **`high`**: Significant user-impacting congestion (utilization > 90%, queue drops > 5,000).
- **`medium`**: Elevated latency or borderline buffer pressure.
- **`low`**: Nominal background traffic or baseline telemetry adherence.
