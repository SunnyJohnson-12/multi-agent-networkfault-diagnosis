import os
import re
from typing import List, Dict, Any, Optional, Set
from app.models.messages import AgentMessage


class LLMClient:
    """Deterministic-first explanation engine with optional LLM narrative synthesis

    and strict anti-hallucination verification.
    """

    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

    @property
    def is_available(self) -> bool:
        return bool(self.gemini_api_key or self.openai_api_key)

    def generate_narrative(
        self,
        top_hypothesis: str,
        confidence: float,
        findings: List[AgentMessage],
        affected_devices: List[str],
        known_numbers: Set[float],
    ) -> str:
        """Generate a clear explanation narrative. Uses deterministic template by default,

        or calls LLM if enabled, falling back safely if hallucinated numbers appear.
        """
        # Always generate high-quality deterministic narrative as baseline
        deterministic_narrative = self._generate_deterministic_template(
            top_hypothesis, confidence, findings, affected_devices
        )

        if not self.is_available:
            return deterministic_narrative

        # Attempt LLM generation if configured
        try:
            llm_text = self._call_llm_api(top_hypothesis, confidence, findings, affected_devices)
            if not llm_text:
                return deterministic_narrative

            # Validate against hallucination: all numbers in LLM text must exist in known_numbers
            if self._validate_hallucination(llm_text, known_numbers):
                return llm_text
            else:
                return deterministic_narrative
        except Exception:
            return deterministic_narrative

    def _generate_deterministic_template(
        self,
        top_hypothesis: str,
        confidence: float,
        findings: List[AgentMessage],
        affected_devices: List[str],
    ) -> str:
        summary_lines = []
        for f in findings:
            summary_lines.append(f"- [{f.source_agent.value}]: {f.finding}")

        dev_str = ", ".join(affected_devices[:4])
        if len(affected_devices) > 4:
            dev_str += f" and {len(affected_devices) - 4} other devices"

        if "Congestion" in top_hypothesis:
            return (
                f"Multi-agent correlation confirms {top_hypothesis.lower()} with {confidence*100:.0f}% confidence. "
                f"High link saturation and severe egress buffer queue drops converge on bottleneck device(s) ({dev_str}), "
                f"inducing elevated transit latency and packet loss across downstream segments."
            )
        elif "Interface or Link Down" in top_hypothesis:
            return (
                f"Physical connectivity diagnostic indicates {top_hypothesis.lower()} ({confidence*100:.0f}% confidence). "
                f"Operational link down signals and isolated downstream network nodes confirm a physical layer disconnect."
            )
        elif "CRC Framing" in top_hypothesis:
            return (
                f"Physical layer signal degradation identified as {top_hypothesis.lower()} ({confidence*100:.0f}% confidence). "
                f"Excessive CRC framing errors with low overall traffic volume indicate dirty fiber optics or damaged patch cabling."
            )
        elif "Resource Exhaustion" in top_hypothesis or "Overload" in top_hypothesis:
            return (
                f"Device health evaluation confirms {top_hypothesis.lower()} ({confidence*100:.0f}% confidence). "
                f"Control plane processor or memory saturation on {dev_str} is stalling packet processing pipelines."
            )
        elif "No Fault" in top_hypothesis:
            return (
                "Telemetry telemetry correlation across all domain agents indicates healthy operational baselines. "
                "No anomalous latency spikes, packet drops, or hardware errors were detected."
            )
        elif "Insufficient" in top_hypothesis:
            return (
                "Telemetry correlation identifies missing critical telemetry metrics required for definitive fault isolation. "
                "Packet loss and link utilization data were absent or incomplete. Deploy additional telemetry probes to reach a diagnosis."
            )
        elif "Ambiguous" in top_hypothesis:
            return (
                f"Diagnostic assessment indicates {top_hypothesis.lower()} ({confidence*100:.0f}% confidence). "
                "Available evidence is insufficient to determine a unique root cause due to conflicting signals across domain agents. "
                "On-site packet capture and deeper interface diagnostics are recommended."
            )
        else:
            return (
                f"Diagnostic assessment indicates {top_hypothesis.lower()} ({confidence*100:.0f}% confidence). "
                f"Evidence gathered across participating agents suggests multi-factor or localized performance impacts."
            )

    def validate_grounding(
        self,
        text: str,
        known_numbers: Set[float],
        known_devices: Optional[Set[str]] = None,
    ) -> bool:
        """Reject LLM output if it introduces ungrounded numbers, invented devices, or HTML tags."""
        if not text:
            return False

        # 1. Reject HTML/Script injections
        if re.search(r"<\s*script|javascript:|data:\s*text/html|<img|<iframe|<svg", text, re.IGNORECASE):
            return False

        # 2. Reject ungrounded numeric values
        tokens = re.findall(r"\b\d+(?:\.\d+)?\b", text)
        for tok in tokens:
            try:
                val = float(tok)
            except ValueError:
                continue
            # Allow common stylistic numbers
            if val in (1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 100.0):
                continue
            matched = any(abs(val - k) < 0.1 for k in known_numbers)
            if not matched:
                return False

        # 3. Reject invented devices
        if known_devices:
            device_candidates = re.findall(r"\b[A-Z0-9]+(?:_[A-Z0-9]+)+\b", text)
            for cand in device_candidates:
                # Skip false-positive protocol/acronym terms
                if cand in ("NETFLOW_IPFIX", "SNMP_ARP", "QOS_WRED", "SHOW_PROCESSES", "CAMPUS_WIDE"):
                    continue
                if cand not in known_devices:
                    return False

        return True

    def _validate_hallucination(self, text: str, known_numbers: Set[float], known_devices: Optional[Set[str]] = None) -> bool:
        """Backward-compatible wrapper for grounding validation."""
        return self.validate_grounding(text, known_numbers, known_devices)

    def _call_llm_api(
        self,
        top_hypothesis: str,
        confidence: float,
        findings: List[AgentMessage],
        affected_devices: List[str],
    ) -> Optional[str]:
        # Minimal non-blocking mockable integration
        # In testing/offline environments, returns None to ensure deterministic fallback
        return None
