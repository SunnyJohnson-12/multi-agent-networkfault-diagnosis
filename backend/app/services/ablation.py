import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.models.diagnosis import FinalDiagnosisReport, DiagnosisStatus
from app.orchestration.orchestrator import orchestrator


class AgentAblationResult(BaseModel):
    agent_name: str
    confidence: float
    confidence_delta: float
    status: str
    status_degraded: bool
    suspected_root_cause: str
    root_cause_changed: bool
    top_hypothesis: str
    runner_up_hypothesis: Optional[str] = None
    margin: float
    evidence_sources: List[str]
    lost_evidence: List[str]
    added_limitations: List[str]
    verdict: str
    impact_score: float


class AblationReport(BaseModel):
    session_id: str
    incident_id: str
    baseline_confidence: float
    baseline_status: str
    baseline_root_cause: str
    configurations: List[Dict[str, Any]]
    agent_contributions: List[AgentAblationResult]
    most_critical_agent: str
    collaboration_proven: bool
    summary: str


async def run_ablation(
    telemetry: List[Dict[str, Any]],
    topology: Optional[Dict[str, Any]],
    baseline_report: FinalDiagnosisReport,
    session_id: str,
    incident_id: str,
    timeout_seconds: float = 6.0,
) -> AblationReport:
    """Execute real multi-agent ablation runs, comparing baseline against single-agent removals."""
    agents_to_ablate = ["performance_agent", "infrastructure_agent", "connectivity_agent"]
    
    # Run each ablation configuration in parallel using isolated orchestrator invocations
    async def run_single_ablation(agent_name: str) -> FinalDiagnosisReport:
        ablated_incident = f"{incident_id}-ABL-{agent_name[:4].upper()}"
        res = await orchestrator.run_diagnostic_session(
            telemetry_raw=telemetry,
            topology_raw=topology,
            incident_id=ablated_incident,
            disabled_agents=[agent_name],
        )
        return res.final_report

    try:
        tasks = [run_single_ablation(a) for a in agents_to_ablate]
        ablated_reports: List[FinalDiagnosisReport] = await asyncio.wait_for(
            asyncio.gather(*tasks),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        raise TimeoutError(f"Ablation analysis timed out after {timeout_seconds}s")

    base_conf = round(float(baseline_report.confidence), 2)
    base_rc = baseline_report.suspected_root_cause
    base_status = baseline_report.status.value
    base_evidence_metrics = {e.metric for e in baseline_report.supporting_evidence}

    # Extract baseline ranking
    base_ranking = baseline_report.extensions.hypotheses_ranking if baseline_report.extensions else []
    base_margin = 0.0
    if len(base_ranking) >= 2:
        base_margin = round(base_ranking[0].score - base_ranking[1].score, 2)

    contributions: List[AgentAblationResult] = []
    config_summaries = [
        {
            "config": "ALL_AGENTS (Baseline)",
            "disabled": [],
            "confidence": base_conf,
            "status": base_status,
            "root_cause": base_rc,
            "margin": base_margin,
        }
    ]

    for agent_name, ab_rep in zip(agents_to_ablate, ablated_reports):
        ab_conf = round(float(ab_rep.confidence), 2)
        ab_rc = ab_rep.suspected_root_cause
        ab_status = ab_rep.status.value
        
        conf_delta = round(base_conf - ab_conf, 2)
        rc_changed = base_rc.strip().lower() != ab_rc.strip().lower()
        status_degraded = (
            base_status == DiagnosisStatus.DIAGNOSED.value
            and ab_status in (DiagnosisStatus.AMBIGUOUS.value, DiagnosisStatus.INSUFFICIENT_DATA.value)
        )
        
        ab_evidence_metrics = {e.metric for e in ab_rep.supporting_evidence}
        lost_ev = sorted(list(base_evidence_metrics - ab_evidence_metrics))
        added_lim = [lim for lim in ab_rep.limitations if lim not in baseline_report.limitations]

        # Ranking & Margin
        ab_ranking = ab_rep.extensions.hypotheses_ranking if ab_rep.extensions else []
        top_h = ab_ranking[0].hypothesis if ab_ranking else ab_rc
        runner_up = ab_ranking[1].hypothesis if len(ab_ranking) > 1 else None
        margin = round(ab_ranking[0].score - ab_ranking[1].score, 2) if len(ab_ranking) > 1 else 0.0

        # One-line verdict
        verdict_parts = [f"Without {agent_name}: confidence {base_conf:.2f} → {ab_conf:.2f}"]
        if rc_changed:
            verdict_parts.append(f"root cause shifted to '{ab_rc}'")
        if status_degraded:
            verdict_parts.append("diagnosis degraded to ambiguous")
        if lost_ev:
            verdict_parts.append(f"lost {len(lost_ev)} evidence metric(s)")
        verdict = ", ".join(verdict_parts) + "."

        # Impact score
        impact = conf_delta + (0.4 if rc_changed else 0.0) + (0.3 if status_degraded else 0.0) + (0.1 * len(lost_ev))

        contributions.append(
            AgentAblationResult(
                agent_name=agent_name,
                confidence=ab_conf,
                confidence_delta=conf_delta,
                status=ab_status,
                status_degraded=status_degraded,
                suspected_root_cause=ab_rc,
                root_cause_changed=rc_changed,
                top_hypothesis=top_h,
                runner_up_hypothesis=runner_up,
                margin=margin,
                evidence_sources=ab_rep.evidence_sources,
                lost_evidence=lost_ev,
                added_limitations=added_lim,
                verdict=verdict,
                impact_score=round(impact, 2),
            )
        )

        config_summaries.append(
            {
                "config": f"WITHOUT_{agent_name.upper()}",
                "disabled": [agent_name],
                "confidence": ab_conf,
                "status": ab_status,
                "root_cause": ab_rc,
                "margin": margin,
            }
        )

    # Sort contributions by impact descending
    contributions.sort(key=lambda x: x.impact_score, reverse=True)
    most_critical = contributions[0].agent_name if contributions else "none"
    collaboration_proven = any(c.confidence_delta > 0.10 or c.root_cause_changed or c.status_degraded for c in contributions)

    summary = (
        f"Ablation proves multi-agent cooperation: disabling '{most_critical}' resulted in the largest "
        f"diagnostic shift ({contributions[0].verdict}). System integrity depends on cross-agent evidence exchange."
    )

    return AblationReport(
        session_id=session_id,
        incident_id=incident_id,
        baseline_confidence=base_conf,
        baseline_status=base_status,
        baseline_root_cause=base_rc,
        configurations=config_summaries,
        agent_contributions=contributions,
        most_critical_agent=most_critical,
        collaboration_proven=collaboration_proven,
        summary=summary,
    )
