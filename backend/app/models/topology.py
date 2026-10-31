from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TopologyNode(BaseModel):
    node_id: str = Field(..., description="Unique node identifier, e.g. HOSTEL_CORE_SW_01")
    name: str = Field(..., description="Human-readable node label")
    node_type: str = Field(..., description="router, switch, access_point, server, workstation, firewall")
    segment: str = Field(..., description="Campus zone: HOSTEL, ACADEMIC, LIBRARY, LABS, DATA_CENTER, BACKBONE")
    ip_address: Optional[str] = None
    status: str = Field("up", description="up, down, degraded")
    model: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TopologyLink(BaseModel):
    link_id: str = Field(..., description="Unique link ID")
    source_node: str = Field(..., description="Source node ID")
    target_node: str = Field(..., description="Target node ID")
    source_interface: str = Field("Gi0/1", description="Interface on source node")
    target_interface: str = Field("Gi0/1", description="Interface on target node")
    bandwidth_mbps: float = Field(1000.0, gt=0.0)
    is_uplink: bool = False
    status: str = Field("up", description="up, down, degraded")
    utilization_pct: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CampusTopology(BaseModel):
    topology_id: str = "CAMPUS-NET-MAIN"
    name: str = "IIT Campus Core & Edge Network Topology"
    nodes: List[TopologyNode]
    links: List[TopologyLink]
