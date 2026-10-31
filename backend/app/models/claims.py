from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field


class ClaimSource(BaseModel):
    """Concrete provenance source linking a diagnostic claim to an agent message."""
    message_id: str = Field(..., description="UUID of the originating agent message")
    source_agent: str = Field(..., description="Role of the agent producing the evidence")
    metric: str = Field(..., description="Specific telemetry or diagnostic metric")
    value: Union[float, int, str, bool] = Field(..., description="Observed value")
    unit: Optional[str] = Field(None, description="Physical unit, e.g. %, ms, pkts")
    device_id: Optional[str] = Field(None, description="Specific device reporting the metric")
    timestamp: Optional[str] = Field(None, description="ISO-8601 timestamp when evidence was produced")
    interpretation: Optional[str] = Field(None, description="Technical rationale of how this evidence supports the claim")


class ReportClaim(BaseModel):
    """An atomic factual claim in the diagnostic report with source citations."""
    claim_id: str = Field(..., description="Unique claim identifier, e.g. C-1, C-2")
    statement: str = Field(..., description="Human-readable factual claim or conclusion")
    claim_type: str = Field(..., description="Type: root_cause | evidence | action | limitation")
    sources: List[ClaimSource] = Field(default_factory=list, description="Linked provenance records")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Claim factual grounding score")
    footnote_tag: str = Field(..., description="Markdown footnote identifier, e.g. [F1]")


class ClaimLedger(BaseModel):
    """Ledger tracking all claims made in a report and verifying total source provenance."""
    session_id: str
    incident_id: str
    claims: List[ReportClaim] = Field(default_factory=list)
    total_claims: int = 0
    grounded_claims: int = 0
    coverage_pct: float = 100.0

    def add_claim(
        self,
        statement: str,
        claim_type: str,
        sources: List[ClaimSource],
        claim_id: Optional[str] = None,
    ) -> ReportClaim:
        cid = claim_id or f"C-{len(self.claims) + 1}"
        footnote_tag = f"[F{len(self.claims) + 1}]"
        
        # Valid source validation
        valid_sources = [s for s in sources if s.message_id and s.source_agent]
        if not valid_sources:
            # Unsupported claim
            claim = ReportClaim(
                claim_id=cid,
                statement=statement,
                claim_type=claim_type,
                sources=[],
                confidence=0.0,
                footnote_tag=footnote_tag,
            )
        else:
            claim = ReportClaim(
                claim_id=cid,
                statement=statement,
                claim_type=claim_type,
                sources=valid_sources,
                confidence=1.0,
                footnote_tag=footnote_tag,
            )

        self.claims.append(claim)
        self.total_claims = len(self.claims)
        self.grounded_claims = sum(1 for c in self.claims if len(c.sources) > 0)
        self.coverage_pct = round((self.grounded_claims / self.total_claims) * 100.0, 1) if self.total_claims > 0 else 100.0
        return claim
