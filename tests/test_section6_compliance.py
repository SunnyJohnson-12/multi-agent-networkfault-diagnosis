import json
import pytest
import jsonschema
from app.orchestration.orchestrator import Orchestrator
from app.models.diagnosis import FinalDiagnosisReport

SECTION_6_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": [
        "incident_id",
        "status",
        "suspected_root_cause",
        "confidence",
        "affected_devices",
        "supporting_evidence",
        "alternative_causes",
        "recommended_actions",
        "evidence_sources",
        "limitations",
    ],
    "properties": {
        "incident_id": {"type": "string"},
        "status": {
            "type": "string",
            "enum": ["diagnosed", "ambiguous", "no_fault_detected", "insufficient_data", "error"],
        },
        "suspected_root_cause": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "affected_devices": {"type": "array", "items": {"type": "string"}},
        "supporting_evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["metric", "value", "interpretation"],
                "properties": {
                    "metric": {"type": "string"},
                    "value": {"type": ["number", "string", "boolean"]},
                    "interpretation": {"type": "string"},
                },
            },
        },
        "alternative_causes": {"type": "array", "items": {"type": "string"}},
        "recommended_actions": {"type": "array", "items": {"type": "string"}},
        "evidence_sources": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "extensions": {"type": "object"},
    },
    "additionalProperties": False,
}


@pytest.mark.asyncio
async def test_section6_schema_compliance():
    orch = Orchestrator()
    telemetry = [
        {
            "device_id": "HOSTEL_CORE_SW_01",
            "device_type": "switch",
            "timestamp": "2026-10-31T20:00:00Z",
            "latency_ms": 280.0,
            "jitter_ms": 35.0,
            "packet_loss_pct": 5.0,
            "link_utilization_pct": 94.0,
            "cpu_utilization_pct": 45.0,
            "memory_utilization_pct": 50.0,
            "queue_drops": 160,
        }
    ]

    rec = await orch.run_diagnostic_session(telemetry_raw=telemetry, incident_id="INC-8832")
    report_dict = rec.final_report.to_section6_dict(include_extensions=False)

    # 1. Strict JSON Schema Validation
    jsonschema.validate(instance=report_dict, schema=SECTION_6_JSON_SCHEMA)

    # 2. Check exact keys
    expected_keys = {
        "incident_id",
        "status",
        "suspected_root_cause",
        "confidence",
        "affected_devices",
        "supporting_evidence",
        "alternative_causes",
        "recommended_actions",
        "evidence_sources",
        "limitations",
    }
    assert set(report_dict.keys()) == expected_keys

    # 3. Check recommendation wording rule
    for action in report_dict["recommended_actions"]:
        assert "Recommended action — human review required." in action

    # 4. Check status allowed values
    assert report_dict["status"] in {"diagnosed", "ambiguous", "no_fault_detected", "insufficient_data", "error"}
