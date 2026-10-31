import random
import copy
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field

from app.validation.validators import ValidationErrorResponse


class FaultInjectionItem(BaseModel):
    target_device_id: str = Field(..., description="Target node in the campus topology")
    metric: str = Field(..., description="Metric: link_utilization_pct, packet_loss_pct, latency_ms, jitter_ms, queue_drops, crc_errors, cpu_utilization_pct, memory_utilization_pct, interface_status")
    value: Union[float, int, str, bool] = Field(..., description="Target value for the metric")


class FaultPreset(BaseModel):
    name: str
    description: str
    target_device: str
    injections: List[Dict[str, Any]]


PRESETS: Dict[str, FaultPreset] = {
    "congestion": FaultPreset(
        name="congestion",
        description="Severe uplink congestion and buffer saturation with coupled queue drops",
        target_device="HOSTEL_CORE_SW_01",
        injections=[
            {"metric": "link_utilization_pct", "value": 96.0},
            {"metric": "queue_drops", "value": 12500},
            {"metric": "latency_ms", "value": 155.0},
            {"metric": "packet_loss_pct", "value": 8.5},
        ],
    ),
    "overload": FaultPreset(
        name="overload",
        description="Control plane CPU and memory exhaustion from protocol churn",
        target_device="DATA_CTR_CORE_01",
        injections=[
            {"metric": "cpu_utilization_pct", "value": 98.0},
            {"metric": "memory_utilization_pct", "value": 94.0},
            {"metric": "latency_ms", "value": 110.0},
        ],
    ),
    "interface_failure": FaultPreset(
        name="interface_failure",
        description="Physical port down causing total downstream link severance",
        target_device="HOSTEL_ACC_SW_01",
        injections=[
            {"metric": "interface_status", "value": "down"},
            {"metric": "packet_loss_pct", "value": 100.0},
            {"metric": "link_utilization_pct", "value": 0.0},
        ],
    ),
    "crc_problem": FaultPreset(
        name="crc_problem",
        description="Physical layer cabling degradation and optical framing corruption",
        target_device="LIB_ACC_SW_01",
        injections=[
            {"metric": "crc_errors", "value": 92},
            {"metric": "packet_loss_pct", "value": 7.8},
            {"metric": "link_utilization_pct", "value": 32.0},
        ],
    ),
    "normal_network": FaultPreset(
        name="normal_network",
        description="Normal healthy network baseline operation with minimal latency and zero packet loss",
        target_device="HOSTEL_CORE_SW_01",
        injections=[
            {"metric": "link_utilization_pct", "value": 35.0},
            {"metric": "packet_loss_pct", "value": 0.05},
            {"metric": "latency_ms", "value": 15.0},
            {"metric": "queue_drops", "value": 0},
            {"metric": "crc_errors", "value": 0},
            {"metric": "cpu_utilization_pct", "value": 28.0},
            {"metric": "memory_utilization_pct", "value": 36.0},
        ],
    ),
    "upstream_dependency": FaultPreset(
        name="upstream_dependency",
        description="Core aggregation uplink dependency bottleneck impacting downstream segments",
        target_device="HOSTEL_CORE_SW_01",
        injections=[
            {"metric": "link_utilization_pct", "value": 88.0},
            {"metric": "queue_drops", "value": 6500},
            {"metric": "latency_ms", "value": 95.0},
            {"metric": "packet_loss_pct", "value": 3.8},
        ],
    ),
    "ambiguous_fault": FaultPreset(
        name="ambiguous_fault",
        description="Conflicting multi-factor telemetry without clear queue buffer exhaustion",
        target_device="ACAD_DIST_SW_02",
        injections=[
            {"metric": "packet_loss_pct", "value": 5.2},
            {"metric": "queue_drops", "value": 0},
            {"metric": "crc_errors", "value": 0},
            {"metric": "link_utilization_pct", "value": 38.0},
            {"metric": "cpu_utilization_pct", "value": 25.0},
            {"metric": "latency_ms", "value": 35.0},
        ],
    ),
}


class FaultInjector:
    """Deterministic, physically-coupled telemetry fault injector for chaos testing."""

    @classmethod
    def inject(
        cls,
        base_telemetry: List[Dict[str, Any]],
        topology: Dict[str, Any],
        injections: Optional[List[Dict[str, Any]]] = None,
        preset: Optional[str] = None,
        couple_metrics: bool = True,
        seed: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        rng = random.Random(seed) if seed is not None else random.Random()

        # Validate topology targets
        valid_node_ids = {n["node_id"] for n in topology.get("nodes", [])}
        if not valid_node_ids:
            # Fallback to telemetry devices if topology is empty
            valid_node_ids = {t["device_id"] for t in base_telemetry}

        final_injections: List[Dict[str, Any]] = []

        if preset:
            if preset not in PRESETS:
                raise ValidationErrorResponse(
                    error_code="INVALID_FAULT_PRESET",
                    message=f"Unknown preset '{preset}'. Must be one of: {list(PRESETS.keys())}",
                    field="preset",
                )
            p = PRESETS[preset]
            target = p.target_device if p.target_device in valid_node_ids else list(valid_node_ids)[0]
            for inj in p.injections:
                final_injections.append({"target_device_id": target, **inj})

        if injections:
            final_injections.extend(injections)

        # Deep copy telemetry to avoid mutating base
        telemetry = copy.deepcopy(base_telemetry)
        device_index = {t["device_id"]: t for t in telemetry}

        for inj in final_injections:
            target_id = inj.get("target_device_id")
            if not target_id or target_id not in valid_node_ids:
                raise ValidationErrorResponse(
                    error_code="INVALID_TARGET_DEVICE",
                    message=f"Target device '{target_id}' is not in campus topology nodes",
                    field="target_device_id",
                )

            metric = inj.get("metric")
            raw_val = inj.get("value")

            if metric not in [
                "link_utilization_pct",
                "packet_loss_pct",
                "latency_ms",
                "jitter_ms",
                "queue_drops",
                "crc_errors",
                "cpu_utilization_pct",
                "memory_utilization_pct",
                "interface_status",
            ]:
                raise ValidationErrorResponse(
                    error_code="INVALID_INJECTION_METRIC",
                    message=f"Unsupported injection metric '{metric}'",
                    field="metric",
                )

            # Find or instantiate device record
            record = device_index.get(target_id)
            if not record:
                record = {
                    "device_id": target_id,
                    "device_type": "switch",
                    "timestamp": "2026-10-31T12:00:00Z",
                    "latency_ms": 12.0,
                    "packet_loss_pct": 0.0,
                    "link_utilization_pct": 25.0,
                    "cpu_utilization_pct": 20.0,
                    "memory_utilization_pct": 30.0,
                }
                telemetry.append(record)
                device_index[target_id] = record

            # Bounds validation
            if metric in ("link_utilization_pct", "packet_loss_pct", "cpu_utilization_pct", "memory_utilization_pct"):
                try:
                    val_float = float(raw_val)
                    if val_float < 0.0 or val_float > 100.0:
                        raise ValueError()
                    record[metric] = round(val_float, 2)
                except Exception:
                    raise ValidationErrorResponse(
                        error_code="INVALID_METRIC_BOUNDS",
                        message=f"{metric} must be a float between 0.0 and 100.0",
                        field=metric,
                    )
            elif metric in ("latency_ms", "jitter_ms"):
                try:
                    val_float = float(raw_val)
                    if val_float < 0.0 or val_float > 5000.0:
                        raise ValueError()
                    record[metric] = round(val_float, 2)
                except Exception:
                    raise ValidationErrorResponse(
                        error_code="INVALID_METRIC_BOUNDS",
                        message=f"{metric} must be a positive float under 5000ms",
                        field=metric,
                    )
            elif metric in ("queue_drops", "crc_errors"):
                try:
                    val_int = int(raw_val)
                    if val_int < 0 or val_int > 2000000:
                        raise ValueError()
                    record[metric] = val_int
                except Exception:
                    raise ValidationErrorResponse(
                        error_code="INVALID_METRIC_BOUNDS",
                        message=f"{metric} must be a non-negative integer under 2,000,000",
                        field=metric,
                    )
            elif metric == "interface_status":
                status_str = str(raw_val).lower()
                if status_str not in ("up", "down"):
                    raise ValidationErrorResponse(
                        error_code="INVALID_INTERFACE_STATUS",
                        message="interface_status must be 'up' or 'down'",
                        field="interface_status",
                    )
                record["interface_status"] = status_str
                if status_str == "down":
                    record["packet_loss_pct"] = 100.0
                    record["link_utilization_pct"] = 0.0

            # Realistic metric coupling
            if couple_metrics:
                util = float(record.get("link_utilization_pct", 0.0))
                if util >= 80.0:
                    delta = (util - 80.0) / 20.0
                    # Queue drops surge exponentially
                    if "queue_drops" not in [i.get("metric") for i in final_injections]:
                        record["queue_drops"] = int((delta ** 2) * 12000 + rng.randint(50, 400))
                    # Buffer queuing induces latency & jitter
                    if "latency_ms" not in [i.get("metric") for i in final_injections]:
                        record["latency_ms"] = round(30.0 + delta * 125.0 + rng.uniform(-3.0, 3.0), 1)
                    if "jitter_ms" not in [i.get("metric") for i in final_injections]:
                        record["jitter_ms"] = round(5.0 + delta * 35.0 + rng.uniform(-1.0, 1.0), 1)
                    # Loss manifests on high utilization
                    if util >= 90.0 and "packet_loss_pct" not in [i.get("metric") for i in final_injections]:
                        loss_delta = (util - 90.0) / 10.0
                        record["packet_loss_pct"] = round(loss_delta * 8.5 + rng.uniform(0.1, 0.5), 1)

        return telemetry
