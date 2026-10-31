from typing import Dict, Any, List, Tuple, Optional
from app.models.diagnosis import HypothesisScore, DiagnosisStatus
from app.models.messages import AgentMessage, AgentRole, SeverityLevel


class HypothesisScoringEngine:
    """Deterministic, transparent hypothesis scoring engine with agreement metrics

    and uncertainty-aware confidence calculation.
    """

    HYPOTHESES = [
        "Bandwidth and Link Congestion",
        "Egress Buffer Queue Exhaustion",
        "Device Control Plane Overload (CPU/Memory)",
        "Physical Interface or Link Down Failure",
        "Physical Layer Cable / CRC Framing Degradation",
        "Upstream Core Dependency Failure",
        "Normal Network Operation (No Fault)",
        "Ambiguous Multi-Factor Degradation",
    ]

    @classmethod
    def evaluate(
        cls,
        findings: List[AgentMessage],
        clarification: Optional[AgentMessage] = None,
        degraded_agents: Optional[List[str]] = None,
        telemetry: Optional[List[Any]] = None,
    ) -> Tuple[str, float, DiagnosisStatus, List[HypothesisScore], List[str]]:
        """Evaluate findings from all available agents, rank competing hypotheses,
        calculate confidence with explainable multi-agent formula, and determine diagnostic status.
        """
        degraded_agents = degraded_agents or []
        scores: Dict[str, float] = {h: 0.05 for h in cls.HYPOTHESES}
        matched: Dict[str, List[str]] = {h: [] for h in cls.HYPOTHESES}
        contradicted: Dict[str, List[str]] = {h: [] for h in cls.HYPOTHESES}
        limitations: List[str] = []

        # 0. Check for Insufficient Telemetry Coverage (Prompt #10 & #16 Scenario F)
        missing_critical: List[str] = []
        if telemetry is not None:
            if len(telemetry) == 0:
                missing_critical = ["packet_loss_pct", "link_utilization_pct", "device_telemetry"]
            else:
                has_loss = any(
                    getattr(t, "packet_loss_pct", None) is not None
                    for t in telemetry
                )
                has_util = any(
                    getattr(t, "link_utilization_pct", None) is not None
                    for t in telemetry
                )
                if not has_loss:
                    missing_critical.append("packet_loss_pct")
                if not has_util:
                    missing_critical.append("link_utilization_pct")

        if missing_critical:
            status = DiagnosisStatus.INSUFFICIENT_EVIDENCE
            top_hyp = "Insufficient Telemetry Coverage"
            confidence = 0.15
            limitations = [
                f"Missing critical telemetry: {', '.join(missing_critical)}",
                "Why it matters: Cannot evaluate network transit degradation, link saturation, or queue buffer state without packet loss and utilization.",
                "Additional telemetry required: Deploy SNMP interface MIB polling or NetFlow/IPFIX stream on access and aggregation switches."
            ]
            ranking_models = [
                HypothesisScore(
                    hypothesis=h,
                    score=0.10,
                    matched_signals=[],
                    contradictory_signals=[],
                    explanation="Critical performance metrics absent; unable to evaluate hypothesis.",
                )
                for h in cls.HYPOTHESES
            ]
            return top_hyp, confidence, status, ranking_models, limitations

        # Extract features from agent messages
        perf_msg = next((m for m in findings if m.source_agent == AgentRole.PERFORMANCE_AGENT), None)
        infra_msg = next((m for m in findings if m.source_agent == AgentRole.INFRASTRUCTURE_AGENT), None)
        conn_msg = next((m for m in findings if m.source_agent == AgentRole.CONNECTIVITY_AGENT), None)

        # 1. Performance Evidence
        high_util = False
        severe_util = False
        high_loss = False
        high_lat = False
        high_jit = False

        util = 0.0
        loss = 0.0
        lat = 0.0
        jit = 0.0

        if perf_msg:
            util = float(perf_msg.metadata.get("max_utilization_pct", 0.0))
            loss = float(perf_msg.metadata.get("max_loss_pct", 0.0))
            lat = float(perf_msg.metadata.get("max_latency_ms", 0.0))
            jit = float(perf_msg.metadata.get("max_jitter_ms", 0.0))

            if util >= 90.0:
                severe_util = True
                high_util = True
                scores["Bandwidth and Link Congestion"] += 0.40
                scores["Egress Buffer Queue Exhaustion"] += 0.25
                matched["Bandwidth and Link Congestion"].append(f"Severe link utilization ({util:.1f}%)")
            elif util >= 75.0:
                high_util = True
                scores["Bandwidth and Link Congestion"] += 0.25
                matched["Bandwidth and Link Congestion"].append(f"Elevated link utilization ({util:.1f}%)")

            if loss >= 3.0:
                high_loss = True
                scores["Bandwidth and Link Congestion"] += 0.20
                scores["Physical Layer Cable / CRC Framing Degradation"] += 0.20
                matched["Bandwidth and Link Congestion"].append(f"Elevated packet loss ({loss:.1f}%)")
                matched["Physical Layer Cable / CRC Framing Degradation"].append(f"Packet loss ({loss:.1f}%)")

            if lat >= 80.0:
                high_lat = True
                scores["Bandwidth and Link Congestion"] += 0.15
                scores["Device Control Plane Overload (CPU/Memory)"] += 0.10
                matched["Bandwidth and Link Congestion"].append(f"High latency ({lat:.1f} ms)")

            if jit >= 25.0:
                high_jit = True
                scores["Bandwidth and Link Congestion"] += 0.10
                scores["Physical Layer Cable / CRC Framing Degradation"] += 0.10
                matched["Bandwidth and Link Congestion"].append(f"Buffer jitter ({jit:.1f} ms)")

            if util < 40.0 and loss < 1.0 and lat < 30.0:
                scores["Normal Network Operation (No Fault)"] += 0.50
                matched["Normal Network Operation (No Fault)"].append("Performance metrics all within standard baseline")
        else:
            limitations.append("Performance agent telemetry unavailable; latency/bandwidth analysis omitted")

        # 2. Infrastructure Evidence
        intf_down = False
        heavy_queue_drops = False
        high_crc = False
        high_cpu = False
        high_mem = False

        cpu = 0.0
        mem = 0.0
        drops = 0
        crc = 0
        down_cnt = 0

        if infra_msg:
            down_cnt = infra_msg.metadata.get("down_interfaces_count", 0)
            drops = infra_msg.metadata.get("total_queue_drops", 0)
            crc = infra_msg.metadata.get("total_crc_errors", 0)
            cpu = float(infra_msg.metadata.get("max_cpu_pct", 0.0))
            mem = float(infra_msg.metadata.get("max_mem_pct", 0.0))

            if down_cnt > 0:
                intf_down = True
                scores["Physical Interface or Link Down Failure"] += 0.70
                matched["Physical Interface or Link Down Failure"].append(f"{down_cnt} interface down state detected")
                contradicted["Normal Network Operation (No Fault)"].append("Interface is physically down")

            if drops > 1000:
                heavy_queue_drops = True
                scores["Bandwidth and Link Congestion"] += 0.25
                scores["Egress Buffer Queue Exhaustion"] += 0.35
                matched["Bandwidth and Link Congestion"].append(f"Massive queue drops ({drops:,})")
                matched["Egress Buffer Queue Exhaustion"].append(f"Hardware buffer overflow ({drops:,} drops)")
            elif drops > 50:
                scores["Egress Buffer Queue Exhaustion"] += 0.20
                matched["Egress Buffer Queue Exhaustion"].append(f"Elevated queue drops ({drops:,})")

            if crc > 50:
                high_crc = True
                scores["Physical Layer Cable / CRC Framing Degradation"] += 0.45
                matched["Physical Layer Cable / CRC Framing Degradation"].append(f"Severe CRC errors ({crc:,})")
                if not high_util:
                    scores["Bandwidth and Link Congestion"] -= 0.15
                    contradicted["Bandwidth and Link Congestion"].append("High CRC errors with low link utilization")

            if cpu >= 85.0:
                high_cpu = True
                scores["Device Control Plane Overload (CPU/Memory)"] += 0.45
                matched["Device Control Plane Overload (CPU/Memory)"].append(f"Critical CPU utilization ({cpu:.1f}%)")
                if not high_util:
                    scores["Bandwidth and Link Congestion"] -= 0.10

            if mem >= 85.0:
                high_mem = True
                scores["Device Control Plane Overload (CPU/Memory)"] += 0.25
                matched["Device Control Plane Overload (CPU/Memory)"].append(f"High memory utilization ({mem:.1f}%)")

            if down_cnt == 0 and drops == 0 and crc == 0 and cpu < 50.0 and mem < 50.0:
                scores["Normal Network Operation (No Fault)"] += 0.40
                matched["Normal Network Operation (No Fault)"].append("Infrastructure health metrics clean")
        else:
            limitations.append("Infrastructure agent health telemetry unavailable; queue drops/hardware checks omitted")

        # 3. Connectivity Evidence
        shared_upstream = False
        isolated_nodes = False

        if conn_msg:
            shared_cnt = conn_msg.metadata.get("shared_count", 0)
            iso_cnt = conn_msg.metadata.get("isolated_nodes_count", 0)
            shared_node = conn_msg.metadata.get("shared_uplink_node")

            if iso_cnt > 0:
                isolated_nodes = True
                scores["Physical Interface or Link Down Failure"] += 0.20
                scores["Upstream Core Dependency Failure"] += 0.35
                matched["Physical Interface or Link Down Failure"].append(f"{iso_cnt} downstream devices isolated")
                matched["Upstream Core Dependency Failure"].append(f"Downstream blast radius isolates {iso_cnt} nodes")

            if shared_cnt >= 3 and shared_node:
                shared_upstream = True
                scores["Bandwidth and Link Congestion"] += 0.15
                scores["Upstream Core Dependency Failure"] += 0.25
                matched["Bandwidth and Link Congestion"].append(
                    f"{shared_cnt} affected devices converge on shared uplink '{shared_node}'"
                )
        else:
            limitations.append("Connectivity agent topology unavailable; blast radius/upstream analysis omitted")

        # 4. Cross-Query Clarification Enhancement
        if clarification and clarification.message_type == AgentRole.CONNECTIVITY_AGENT or (
            clarification and clarification.source_agent == AgentRole.CONNECTIVITY_AGENT
        ):
            shared_pct = float(clarification.metadata.get("shared_percentage", 0.0))
            verified_node = clarification.metadata.get("verified_upstream")
            if shared_pct >= 75.0 and verified_node:
                scores["Bandwidth and Link Congestion"] += 0.15
                matched["Bandwidth and Link Congestion"].append(
                    f"Cross-query confirmed: {shared_pct:.0f}% of affected nodes bottleneck on '{verified_node}'"
                )
                scores["Upstream Core Dependency Failure"] += 0.10

        # Check for Conflicting Evidence Case (Prompt #9)
        # Performance shows elevated loss, but switch buffers, CPU, memory, CRC framing are all clean, and paths differ
        is_conflicting = (
            high_loss
            and not heavy_queue_drops
            and drops <= 10
            and cpu < 55.0
            and mem < 55.0
            and crc <= 10
            and not intf_down
            and not shared_upstream
        )

        if is_conflicting:
            scores["Bandwidth and Link Congestion"] = 0.48
            scores["Physical Layer Cable / CRC Framing Degradation"] = 0.43
            scores["Upstream Core Dependency Failure"] = 0.09
            matched["Bandwidth and Link Congestion"].append("Elevated packet loss observed on flow")
            matched["Physical Layer Cable / CRC Framing Degradation"].append("Potential uncounted framing loss or transceiver attenuation")
            contradicted["Bandwidth and Link Congestion"].append("Zero queue drops logged in switch buffer")
            contradicted["Physical Layer Cable / CRC Framing Degradation"].append("CRC hardware counters show 0 errors")

        # Penalize hypotheses with contradictory signals
        if intf_down:
            scores["Bandwidth and Link Congestion"] *= 0.3
            scores["Normal Network Operation (No Fault)"] = 0.0

        if severe_util and heavy_queue_drops:
            # Clear congestion signature
            scores["Physical Layer Cable / CRC Framing Degradation"] *= 0.5
            scores["Device Control Plane Overload (CPU/Memory)"] *= 0.6

        if high_crc and not high_util:
            # Physical medium problem
            scores["Physical Layer Cable / CRC Framing Degradation"] += 0.25

        # Normalize scores to [0.0, 1.0]
        max_possible = max(scores.values()) or 1.0
        normalized_scores: Dict[str, float] = {}
        for h, raw in scores.items():
            val = min(1.0, max(0.02, raw / max_possible if max_possible > 1.0 else raw))
            normalized_scores[h] = round(val, 2)

        # Sort hypotheses by score descending
        ranked = sorted(normalized_scores.items(), key=lambda x: x[1], reverse=True)
        top_hyp, top_score = ranked[0]
        second_hyp, second_score = ranked[1]

        # Determine Diagnostic Status
        score_diff = top_score - second_score
        status = DiagnosisStatus.DIAGNOSED

        if is_conflicting:
            status = DiagnosisStatus.AMBIGUOUS
            top_hyp = "Ambiguous Multi-Factor Degradation"
            limitations.append(
                "Available evidence is insufficient to determine a unique root cause. "
                "Conflicting signals: elevated packet loss without corresponding hardware queue buffer drops or control plane overload."
            )
        elif score_diff <= 0.12 and top_score > 0.35 and top_hyp != "Normal Network Operation (No Fault)":
            status = DiagnosisStatus.AMBIGUOUS
            top_hyp = "Ambiguous Multi-Factor Degradation"
            limitations.append(
                f"Available evidence is insufficient to determine a unique root cause. "
                f"Close competing hypotheses: '{ranked[0][0]}' ({top_score:.2f}) vs '{second_hyp}' ({second_score:.2f}). On-site packet capture recommended."
            )
        elif top_hyp == "Normal Network Operation (No Fault)":
            status = DiagnosisStatus.NO_FAULT_DETECTED

        # --- DETERMINISTIC EXPLAINABLE CONFIDENCE FORMULA ---
        # Confidence = 0.35*Evidence_Strength + 0.25*Agent_Agreement + 0.20*Evidence_Coverage + 0.20*Hypothesis_Separation
        #              - Conflict_Penalty - Missing_Penalty - Degraded_Penalty
        evidence_strength = min(1.0, (len(matched[top_hyp]) * 0.22) + (top_score * 0.45))

        def agent_supports_hyp(role: AgentRole) -> bool:
            sigs = " ".join(matched[top_hyp]).lower()
            if role == AgentRole.PERFORMANCE_AGENT:
                return any(k in sigs for k in ("utilization", "loss", "latency", "jitter", "baseline"))
            if role == AgentRole.INFRASTRUCTURE_AGENT:
                return any(k in sigs for k in ("queue", "drop", "cpu", "mem", "crc", "interface down", "hardware"))
            if role == AgentRole.CONNECTIVITY_AGENT:
                return any(k in sigs for k in ("uplink", "converge", "isolated", "bottleneck", "blast radius"))
            return False

        supporting_agent_count = sum(
            1 for msg in findings
            if agent_supports_hyp(msg.source_agent)
        )
        total_active_agents = max(1, len(findings))
        agent_agreement = min(1.0, supporting_agent_count / total_active_agents) if total_active_agents > 0 else 0.5
        if supporting_agent_count >= 2:
            agent_agreement = max(agent_agreement, 0.90)
        if supporting_agent_count >= 3:
            agent_agreement = 1.0

        domains_present = sum(
            1 for role in (AgentRole.PERFORMANCE_AGENT, AgentRole.INFRASTRUCTURE_AGENT, AgentRole.CONNECTIVITY_AGENT)
            if any(f.source_agent == role for f in findings)
        )
        evidence_coverage = domains_present / 3.0
        hypothesis_separation = max(0.0, min(1.0, score_diff * 2.0))

        conflict_penalty = 0.20 if contradicted[top_hyp] or is_conflicting else 0.0
        missing_penalty = 0.10 * (3 - domains_present)
        degraded_penalty = 0.15 * len(degraded_agents)

        raw_confidence = (
            0.35 * evidence_strength
            + 0.25 * agent_agreement
            + 0.20 * evidence_coverage
            + 0.20 * hypothesis_separation
            - conflict_penalty
            - missing_penalty
            - degraded_penalty
        )

        if status == DiagnosisStatus.NO_FAULT_DETECTED:
            cleanliness = 1.0 - max(util / 100.0, loss / 10.0, lat / 100.0, cpu / 100.0) if perf_msg and infra_msg else 0.8
            confidence = round(min(0.95, max(0.70, 0.76 + 0.18 * cleanliness - degraded_penalty)), 2)
        elif status == DiagnosisStatus.AMBIGUOUS:
            confidence = round(min(0.50, max(0.35, raw_confidence)), 2)
        else:
            confidence = round(min(0.96, max(0.40, raw_confidence)), 2)

        if degraded_agents:
            for da in degraded_agents:
                limitations.append(f"Diagnosis generated with degraded agent availability: '{da}' did not contribute.")

        # Build detailed HypothesisScore models
        ranking_models = []
        for h, s in ranked:
            explanation = ""
            if matched[h]:
                explanation = "Supported by: " + "; ".join(matched[h])
            else:
                explanation = "Insufficient signal correlation"
            if contradicted[h]:
                explanation += " | Contradicted by: " + "; ".join(contradicted[h])

            ranking_models.append(
                HypothesisScore(
                    hypothesis=h,
                    score=s,
                    matched_signals=matched[h],
                    contradictory_signals=contradicted[h],
                    explanation=explanation,
                )
            )

        return top_hyp, confidence, status, ranking_models, limitations
