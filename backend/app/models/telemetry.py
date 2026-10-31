from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


class BaselineMetrics(BaseModel):
    baseline_latency_ms: Optional[float] = Field(None, ge=0.0)
    baseline_jitter_ms: Optional[float] = Field(None, ge=0.0)
    baseline_packet_loss_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    baseline_throughput_mbps: Optional[float] = Field(None, ge=0.0)
    baseline_link_utilization_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    baseline_cpu_utilization_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    baseline_memory_utilization_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    baseline_queue_drops: Optional[int] = Field(None, ge=0)
    baseline_crc_errors: Optional[int] = Field(None, ge=0)


class DeviceTelemetry(BaseModel):
    device_id: str = Field(..., min_length=1, description="Unique identifier of device")
    device_name: Optional[str] = None
    device_type: str = Field(
        ...,
        description="Type of network node (e.g., router, switch, access_point, server, workstation, firewall)",
    )
    interface: Optional[str] = Field(None, description="Monitored interface name")
    timestamp: str = Field(..., description="ISO-8601 timestamp")
    
    # Performance metrics
    latency_ms: Optional[float] = Field(None, ge=0.0, description="One-way or round-trip latency in milliseconds")
    jitter_ms: float = Field(0.0, ge=0.0, description="Packet jitter in milliseconds")
    packet_loss_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Packet loss percentage [0-100]")
    throughput_mbps: float = Field(0.0, ge=0.0, description="Measured network throughput in Mbps")
    bandwidth_capacity_mbps: float = Field(1000.0, gt=0.0, description="Interface link bandwidth capacity in Mbps")
    link_utilization_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Interface link utilization percentage [0-100]")
    
    # Infrastructure health metrics
    cpu_utilization_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Device CPU utilization percentage [0-100]")
    memory_utilization_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Device RAM utilization percentage [0-100]")
    interface_status: str = Field(
        "up",
        description="Operational status of the interface: up, down, degraded, admin_down",
    )
    queue_drops: int = Field(0, ge=0, description="Egress/ingress buffer queue drops count")
    crc_errors: int = Field(0, ge=0, description="Cyclic Redundancy Check / framing errors count")
    temperature_c: Optional[float] = None
    
    # Comparative baselines
    baseline: Optional[BaselineMetrics] = None
    
    # Arbitrary tags / metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("interface_status")
    @classmethod
    def validate_interface_status(cls, v: str) -> str:
        allowed = {"up", "down", "degraded", "admin_down"}
        if v.lower() not in allowed:
            raise ValueError(f"interface_status must be one of {allowed}, got '{v}'")
        return v.lower()


class TelemetryBatch(BaseModel):
    batch_id: Optional[str] = None
    timestamp: Optional[str] = None
    records: List[DeviceTelemetry] = Field(..., min_length=1)
