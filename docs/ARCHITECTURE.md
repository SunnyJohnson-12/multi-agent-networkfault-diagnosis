# System Architecture & Technical Design

## 1. Executive Summary
**The Signal Room** is an autonomous, evidence-based Multi-Agent Network Fault Diagnosis System designed for large-scale enterprise campus networks. Rather than relying on a generic monolithic LLM or chatbot, the system decouples network diagnostic reasoning into five domain-specialized agents communicating over a validated JSON protocol.

---

## 2. Core Architectural Pillars

### 2.1 Deterministic-First, LLM-Second
1. **Telemetry Anomaly Detection**: Threshold and baseline-deviation algorithms independently run by Performance and Infrastructure agents.
2. **Graph Dependency Traversal**: NetworkX directed graph analysis for blast radius and shared upstream bottleneck detection by the Connectivity Agent.
3. **Transparent Hypothesis Scoring Engine**: A deterministic weighted rule engine evaluating competing hypotheses against corroborating and contradictory signals.
4. **Anti-Hallucination LLM Synthesis**: Optional LLM refinement is strictly validated: every numeric token in the narrative must exist in the session telemetry, otherwise the system safely reverts to the deterministic template.

### 2.2 Proof of Genuine Multi-Agent Collaboration
- **Dynamic Cross-Queries**: The Correlation Agent initiates follow-up queries to the Connectivity Agent to resolve ambiguities before committing to a root-cause candidate.
- **Agent Interdependence Proof**: Removing an agent's findings visibly degrades diagnostic confidence and dynamically alters the hypothesis leaderboard.
- **Degraded-Mode Resilience**: If an agent times out or fails, the orchestrator penalizes confidence and explicitly records the blind spot under `limitations`.

---

## 3. The 5 Specialized Agents

```
+-----------------------------------------------------------------------------------+
| 1. Performance Agent (performance_agent)                                         |
|    - Evaluates link utilization, latency, jitter, loss, throughput baselines      |
|    - Detects link saturation, buffer queuing oscillation, and transmission drops  |
+-----------------------------------------------------------------------------------+
| 2. Infrastructure Agent (infrastructure_agent)                                   |
|    - Evaluates hardware health: CPU load, memory utilization, queue drops, CRC    |
|    - Distinguishes control-plane starvation from physical transceiver failure     |
+-----------------------------------------------------------------------------------+
| 3. Connectivity Agent (connectivity_agent)                                       |
|    - Evaluates campus graph topology, link hierarchy, and dependency blast radius |
|    - Responds to dynamic cross-queries regarding shared upstream bottlenecks       |
+-----------------------------------------------------------------------------------+
| 4. Correlation Agent (correlation_agent)                                         |
|    - Bundles all domain findings; drives the Hypothesis Race                       |
|    - Synthesizes corroborating and contradictory evidence into a unified verdict   |
+-----------------------------------------------------------------------------------+
| 5. Reporting Agent (reporting_agent)                                             |
|    - Produces strict Section 6 JSON, executive Markdown, and simulated remediation|
|    - Enforces mandatory human-in-the-loop review phrasing                         |
+-----------------------------------------------------------------------------------+
```

---

## 4. Central Orchestrator & Asynchronous Bus
- **Session Lifecycle**: Assigns session IDs (`DX-YYYY-NNNN`) and incident numbers (`INC-XXXX`).
- **Parallel Dispatch**: Domain agents execute concurrently via `asyncio.gather` bounded by execution timeouts.
- **Event Bus & Streaming**: In-memory pub/sub message bus records immutable message history and streams events in real-time to the React dashboard via Server-Sent Events (SSE).
- **Session Persistence**: Complete session records (telemetry, topology, raw protocol messages, Section 6 report, Markdown report) are persisted as JSON files.

---

## 5. Transparent Hypothesis Scoring Engine

| Hypothesis | Key Positive Signals | Contradictory Signals |
|---|---|---|
| **Bandwidth and Link Congestion** | Link util >= 90%, Queue drops > 1000, Latency > 100ms, Shared uplink confirmed | Interface down, High CRC with low util |
| **Egress Buffer Queue Exhaustion** | Queue drops > 1000, Loss > 3%, Jitter > 25ms | Queue drops == 0 |
| **Device Control Plane Overload** | CPU >= 85%, Memory >= 85%, Latency elevated | CPU < 50%, Memory < 50% |
| **Physical Interface or Link Down** | Interface status == "down", Unreachable downstream nodes | Link utilization > 0, Interface status == "up" |
| **Physical Layer / CRC Degradation** | CRC errors > 50, Packet loss > 5% with low link utilization | CRC errors == 0 |
| **Normal Network Operation** | All metrics within baseline, Zero drops/CRC | Any critical threshold breached |
| **Ambiguous Multi-Factor** | Top two hypotheses within 0.08 score margin | Single hypothesis lead >= 0.20 |

---

## 6. Strict Section 6 Output Compliance
All generated diagnostic reports adhere strictly to the JSON schema defined in Section 6:
```json
{
  "incident_id": "INC-8832",
  "status": "diagnosed",
  "suspected_root_cause": "Severe link congestion and egress buffer queue saturation on HOSTEL_CORE_SW_01",
  "confidence": 0.88,
  "affected_devices": ["HOSTEL_CORE_SW_01", "HOSTEL_ACC_SW_01"],
  "supporting_evidence": [
    { "metric": "link_utilization_pct", "value": 96.0, "interpretation": "Critical link saturation" },
    { "metric": "queue_drops", "value": 14230, "interpretation": "Elevated egress queue drops" }
  ],
  "alternative_causes": ["Egress Buffer Queue Exhaustion"],
  "recommended_actions": [
    "Inspect upstream and egress link utilization on HOSTEL_CORE_SW_01 — Recommended action — human review required.",
    "Review queue configuration, WRED thresholds, and traffic distribution — Recommended action — human review required."
  ],
  "evidence_sources": ["performance_agent", "infrastructure_agent", "connectivity_agent"],
  "limitations": ["Root cause based on telemetry snapshot; on-site verification recommended"],
  "extensions": {
    "session_id": "DX-2026-0001",
    "severity": "critical",
    "scope": "Campus-Wide Aggregation",
    "hypotheses_ranking": [...],
    "simulated_remediation": {...}
  }
All supplemental analytics reside exclusively within the optional `extensions` object, ensuring 100% adherence to standard enterprise automation requirements.

---

## 7. Advanced Features Pack Architecture

### 7.1 Agent Ablation Engine (`services/ablation.py`)
- Executes parallel, isolated orchestrator pipelines across all agent permutations (`ALL`, `WITHOUT_PERFORMANCE`, `WITHOUT_INFRASTRUCTURE`, `WITHOUT_CONNECTIVITY`).
- Computes empirical confidence deltas, root-cause shift, degradation flags, lost evidence metrics, and per-agent impact scores.
- Fully isolated in memory: baseline session record is never overwritten or mutated.
- Exposes `POST /api/diagnosis/{id}/ablation` and `GET /api/diagnosis/{id}/ablation`.

### 7.2 Fault Injection Studio (`services/fault_injector.py`)
- Provides an interactive chaos laboratory generating synthetic telemetry on top of a healthy network baseline (`01_normal_network.json`).
- Validates all injection target nodes against the campus topology graph; rejects out-of-range metrics with RFC 7807 error envelopes.
- Implements transparent physical coupling (e.g. saturation couples with queue drops and latency noise) with seeded PRNG (`seed` parameter) for deterministic replayability.
- Exposes `GET /api/inject/presets`, `POST /api/inject`, and `POST /api/inject/diagnose`.

### 7.3 Calibrated Confidence Engine (`services/calibration.py`)
- Benchmarks diagnostic confidence against ground truth using Monte Carlo randomized variants across all 6 fault classes.
- Computes Expected Calibration Error (ECE across 10 bins), empirical accuracy, confusion matrix, and mean confidence separation.
- Enforces an uncertainty cap ($\le 0.65$) on ambiguous incidents to prevent overconfident hallucinations.
- Persists reports to `data/calibration/report.json` and exposes `GET /api/calibration`.

### 7.4 ClaimLedger & Evidence-to-Claim Traceability (`models/claims.py`)
- Deconstructs every root cause, evidence interpretation, device attribution, and recommendation into an atomic `ReportClaim`.
- Maps each claim to underlying agent message IDs with exact metric, value, unit, and device attribution.
- Renders Markdown footnote citations (`[F1]`, `[F2]`) mapped to a Traceability Reference Index.
- Enforces a 100% coverage target under `extensions.traceability` and provides `GET /api/diagnosis/{id}/claims`.

