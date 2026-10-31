# The Signal Room: Multi-Agent Network Fault Diagnosis System

> **Autonomous multi-agent telemetry correlation, topology blast radius heatmapping, and evidence-based root-cause diagnosis for enterprise campus networks.**

---

## 1. Problem Statement
In mission-critical enterprise environments like an IIT campus (hostels, academic blocks, central library, high-performance computing labs, and data centers), network anomalies often present as complex, compounding symptoms. A sudden evening traffic spike can saturate an aggregation uplink, cause tens of thousands of buffer drops, induce multi-switch latency jitter, and degrade dozens of downstream access points simultaneously.

Traditional monitoring systems inundate network engineers with disconnected alerts. Monolithic LLM chatbots hallucinate numbers or lack verifiable access to topology structure. Network Operations Centers (NOCs) require an evidence-backed system where **specialized autonomous agents independently analyze distinct telemetry dimensions, exchange structured findings over a documented protocol, correlate evidence, and converge on one unified, uncertainty-aware diagnosis.**

---

## 2. Solution Overview
**The Signal Room** is a deterministic-first multi-agent system comprising five specialized autonomous agents:
1. **Performance Agent**: Evaluates bandwidth utilization, latency, jitter, and packet loss deviations from baselines.
2. **Infrastructure Agent**: Assesses hardware buffer queue exhaustion, CPU/memory pressure, interface state, and physical CRC framing errors.
3. **Connectivity Agent**: Traverses the campus topology graph, models downstream dependency blast radii, and identifies shared bottlenecks.
4. **Correlation Agent**: Bundles domain findings, conducts dynamic cross-query inquiries with peer agents, deterministically scores competing hypotheses, and isolates the root cause.
5. **Reporting Agent**: Formats the consensus verdict into strict Section 6 JSON, generates executive Markdown summaries, and projects simulated remediation impacts.

---

## 3. Why Multi-Agent?
- **Decoupled Analytical Lenses**: Telemetry saturation, hardware buffer exhaustion, and graph dependencies require completely distinct analytical models (statistical baselines, hardware register auditing, and graph traversal).
- **Verifiable Inter-Agent Deliberation**: The Correlation Agent dynamically queries the Connectivity Agent (`clarification_request` → `clarification_response`) to confirm shared upstream bottlenecks before locking in a diagnosis.
- **Empirical Collaboration Proof ("The Missing Agent Test")**: Removing or disabling an agent visibly shifts hypothesis scores and reduces diagnostic certainty, proving genuine multi-agent interdependence.

---

## 4. System Architecture

```
                                      +-----------------------------+
                                      |   FastAPI Application       |
                                      |   - REST API Endpoints      |
                                      |   - SSE Agent Event Stream  |
                                      +--------------+--------------+
                                                     |
                                      +--------------v--------------+
                                      |     Central Orchestrator    |
                                      |   - Session Manager (DX-..) |
                                      |   - Agent Dispatch & Timeout|
                                      |   - Degraded Mode Handler   |
                                      +--------------+--------------+
                                                     |
                         +---------------------------+---------------------------+
                         |                           |                           |
                 (Async Broadcast)           (Findings Route)            (Final Route)
                         |                           |                           |
            +------------v-----------+               |                           |
            |   In-Memory Event Bus  |               |                           |
            |   - Session Message Log|               |                           |
            |   - Real-Time SSE Feed |               |                           |
            +---+--------+-------+---+               |                           |
                |        |       |                   |                           |
+---------------+--+ +---+-------+----+ +------------+----+                      |
| Performance Agent| | Infrastructure | |  Connectivity   |                      |
| - Congestion     | | Agent          | |  Agent          |                      |
| - Latency/Jitter | | - CPU / RAM    | |  - Graph BFS    |                      |
| - Packet Loss    | | - Drops / CRC  | |  - Shared Upstream                     |
+-------+----------+ +---+-------+----+ +----+-------+----+                      |
        |                |                   |       ^                           |
        +----------------+-------------------+       |                           |
                         | (diagnostic_finding)      | (clarification_query)     |
                         v                           v                           |
            +----------------------------------------+----+                      |
            |            Correlation Agent                |                      |
            |  - Evidence Bundler                         |                      |
            |  - Deterministic Hypothesis Scoring Engine  |                      |
            |  - Dynamic Cross-Query Coordinator          |                      |
            |  - Confidence & Limitation Evaluator        |                      |
            |  - Anti-Hallucination Explainer             |                      |
            +--------------------+------------------------+                      |
                                 | (consolidated_diagnosis)                      |
                                 v                                               |
            +---------------------------------------------+                      |
            |              Reporting Agent                |                      |
            |  - Section 6 Compliant JSON Generator       |                      |
            |  - Executive Markdown Report Generator      |<---------------------+
            |  - Simulated Remediation Impact Modeling    |
            +--------------------+------------------------+
                                 | (final_report)
                                 v
            +---------------------------------------------+
            |      File-based Session Store (JSON / MD)   |
            +---------------------------------------------+
```

---

## 5. The 5 Specialized Agents

| Agent | Responsibilities | Key Metrics Evaluated | Sample Finding |
|---|---|---|---|
| **Performance Agent** (`performance_agent`) | Latency, jitter, packet loss, bandwidth capacity, and link utilization baselines | `link_utilization_pct`, `latency_ms`, `packet_loss_pct`, `jitter_ms` | *"Severe link congestion detected on HOSTEL_CORE_SW_01 uplink (96.0% utilization, 8.2% packet loss)"* |
| **Infrastructure Agent** (`infrastructure_agent`) | Hardware health, CPU/RAM exhaustion, egress queue drops, and physical CRC errors | `queue_drops`, `crc_errors`, `cpu_utilization_pct`, `interface_status` | *"Egress queue congestion: 14,230 buffer drops logged across hardware queues"* |
| **Connectivity Agent** (`connectivity_agent`) | Campus topology graph, path dependency, blast radius, and shared uplink identification | `affected_topology_nodes`, `shared_upstream_bottleneck`, `isolated_nodes` | *"Topology bottleneck identified: 12 affected access devices converge on shared upstream switch 'HOSTEL_CORE_SW_01'"* |
| **Correlation Agent** (`correlation_agent`) | Bundles findings, coordinates cross-queries, runs the Hypothesis Race, computes confidence | `diagnostic_confidence`, hypothesis scores, limitation flags | Cross-queries Connectivity Agent to verify shared bottleneck; settles root cause at 88% confidence |
| **Reporting Agent** (`reporting_agent`) | Produces strict Section 6 JSON, Markdown reports, and simulated remediation projections | Section 6 JSON schema, markdown report, simulation deltas | Compiles unified report with mandatory human-review safety tags |

---

## 6. Inter-Agent Diagnostic Message Protocol (IADMP)
Every message conforms to version `1.0` and is validated via Pydantic v2:

```json
{
  "message_id": "b3e0c0a5-8120-4df7-8023-388274112e4d",
  "session_id": "DX-2026-0001",
  "timestamp": "2026-10-31T21:00:02Z",
  "source_agent": "correlation_agent",
  "target_agent": "connectivity_agent",
  "message_type": "clarification_request",
  "schema_version": "1.0",
  "device_ids": ["HOSTEL_CORE_SW_01"],
  "metric": "shared_uplink_dependency",
  "value": 12,
  "unit": "devices",
  "severity": "high",
  "finding": "Clarification query: verify if 12 affected devices funnel through upstream node 'HOSTEL_CORE_SW_01'",
  "evidence": [...],
  "confidence": 0.88,
  "possible_causes": ["Bandwidth congestion on uplink"],
  "recommended_checks": ["Inspect interface link saturation"],
  "in_reply_to": "msg-003",
  "metadata": {"suspected_bottleneck": "HOSTEL_CORE_SW_01"}
}
```
*See [docs/AGENT_PROTOCOL.md](docs/AGENT_PROTOCOL.md) for full field specifications and error codes.*

---

## 7. Technology Stack
- **Backend**: Python 3.9+, FastAPI, Pydantic v2, NetworkX, Uvicorn, Pytest, Rich.
- **Frontend**: React 18, Vite, TypeScript, Lucide Icons, Vanilla CSS Design System.
- **Communication**: REST API + Server-Sent Events (SSE).
- **Storage**: Thread-safe file-backed JSON session persistence (`data/sessions/`).

---

## 8. Installation & Setup

### Prerequisites
- Python 3.9+
- Node.js 18+ and npm

### 1. Clone & Set Up Python Environment
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt
```

### 2. Set Up Frontend Environment
```bash
cd frontend
npm install
cd ..
```

### 3. Environment Variables (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Note: System operates 100% deterministically without API keys. Optional `GEMINI_API_KEY` or `OPENAI_API_KEY` may be provided for LLM narrative enhancement; any number not present in telemetry is rejected to prevent hallucinations).*

---

## 9. Running Backend, Frontend, Tests & Demo

### 1. Run Standalone Reproducible CLI Demo (Single Command)
```bash
source .venv/bin/activate

# Flagship Autonomous Walkthrough
python demo.py --scenario 07_hackathon_demo.json

# Feature 1: Agent Ablation Analysis (Collaboration Proof)
python demo.py --ablation

# Feature 2: Fault Injection Studio (Chaos Engine)
python demo.py --inject congestion --seed 7

# Feature 3: Calibrated Confidence & ECE Benchmark
python demo.py --calibrate --runs 30

# Feature 4: Evidence-to-Claim Traceability (ClaimLedger & Footnotes)
python demo.py --trace
```

### 2. Run Automated Pytest Test Suite
```bash
source .venv/bin/activate
pytest -v
```

### 3. Run FastAPI Backend
```bash
source .venv/bin/activate
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```
API Documentation available at: `http://localhost:8000/docs`

### 4. Run React Dashboard ("The Signal Room")
```bash
cd frontend
npm run dev
```
Open Dashboard at: `http://localhost:5173`

---

## 10. Preconfigured Campus Scenarios

| Scenario | File | Description | Expected Diagnosis |
|---|---|---|---|
| **1. Normal Baseline** | `01_normal_network.json` | All campus segments operating within normal baselines | `no_fault_detected` (Normal Baseline) |
| **2. Bandwidth Congestion** | `02_bandwidth_congestion.json` | Evening peak streaming saturating Hostel Core switch uplink | `diagnosed` (Bandwidth and Link Congestion) |
| **3. Device Overload** | `03_device_overload.json` | Flapping route table causing 92% CPU and 89% RAM saturation | `diagnosed` (Device Control Plane Resource Exhaustion) |
| **4. Interface Failure** | `04_interface_failure.json` | Physical link down on Library distribution switch isolating APs | `diagnosed` (Physical Interface or Link Down Failure) |
| **5. CRC Degradation** | `05_crc_error_degradation.json` | Dirty optical fiber generating 1,840 CRC errors with low utilization | `diagnosed` (Physical Layer Cable / CRC Framing Degradation) |
| **6. Ambiguous Fault** | `06_ambiguous_fault.json` | Borderline simultaneous load (76% util) and CPU (74%) | `ambiguous` (Explicit uncertainty, ranked hypotheses) |
| **7. Hackathon Demo** | `07_hackathon_demo.json` | Uplink 96%, loss 8.2%, latency 145ms, drops 14,230, 12 affected nodes | `diagnosed` (Severe link congestion & buffer queue saturation) |
| **8. Degraded Agent** | `08_degraded_agent_timeout.json` | Infrastructure Agent disabled/timed out; system degrades gracefully | `diagnosed` (Lower confidence, recorded in limitations) |

---

## 11. REST API Overview
- `POST /api/diagnose`: Ingests telemetry, executes all agents, returns Section 6 report.
- `POST /api/telemetry`: Validates and accepts telemetry batch.
- `GET /api/diagnosis/{id}`: Returns diagnostic report by session or incident ID.
- `GET /api/diagnosis/{id}/messages`: Returns raw protocol message audit trail.
- `GET /api/diagnosis/{id}/findings`: Returns domain findings and cross-query exchanges.
- `GET /api/diagnosis/{id}/report.md`: Returns executive Markdown report.
- `GET /api/scenarios`: Lists all available scenarios.
- `POST /api/scenarios/{name}/run`: Executes a scenario with optional agent disabling.
- `GET /api/diagnosis/{id}/stream`: Real-time Server-Sent Events (SSE) feed.
- `GET /api/health`: System health and active agent status.
- `GET /api/topology`: Complete campus network topology.

---

## 12. Example Section 6 Compliant Report

```json
{
  "incident_id": "INC-8832",
  "status": "diagnosed",
  "suspected_root_cause": "Severe link congestion and egress buffer queue saturation on HOSTEL_CORE_SW_01",
  "confidence": 0.88,
  "affected_devices": [
    "HOSTEL_CORE_SW_01",
    "HOSTEL_ACC_SW_01",
    "HOSTEL_ACC_SW_02",
    "HOSTEL_AP_01"
  ],
  "supporting_evidence": [
    {
      "metric": "link_utilization_pct",
      "value": 96.0,
      "interpretation": "Critical link saturation (96.0% >= 90% threshold), baseline was 42.0%"
    },
    {
      "metric": "queue_drops",
      "value": 14230,
      "interpretation": "Elevated egress queue drops (14,230 packets) due to buffer exhaustion"
    },
    {
      "metric": "latency_ms",
      "value": 145.0,
      "interpretation": "Severe round-trip latency (145.0 ms) (baseline was 12.0 ms)"
    }
  ],
  "alternative_causes": [
    "Egress Buffer Queue Exhaustion",
    "Upstream Core Dependency Failure"
  ],
  "recommended_actions": [
    "Inspect upstream and egress link utilization on HOSTEL_CORE_SW_01 — Recommended action — human review required.",
    "Review queue configuration, WRED thresholds, and traffic distribution — Recommended action — human review required.",
    "Apply rate-limiting or traffic shaping to non-critical bulk flows — Recommended action — human review required."
  ],
  "evidence_sources": [
    "connectivity_agent",
    "infrastructure_agent",
    "performance_agent"
  ],
  "limitations": [
    "Root cause based on telemetry snapshot; on-site verification recommended"
  ],
  "extensions": {
    "session_id": "DX-2026-0001",
    "severity": "critical",
    "scope": "Campus-Wide Aggregation",
    "hypotheses_ranking": [
      {
        "hypothesis": "Bandwidth and Link Congestion",
        "score": 0.88,
        "explanation": "Supported by: Severe link utilization (96.0%); Massive queue drops (14,230); High latency (145.0 ms)"
      },
      {
        "hypothesis": "Egress Buffer Queue Exhaustion",
        "score": 0.58,
        "explanation": "Supported by: Hardware buffer overflow (14,230 drops)"
      }
    ],
    "simulated_remediation": {
      "action_type": "Dynamic Traffic Shaping & Queue Reallocation",
      "estimated_impact": "Traffic shaping would reduce estimated link utilization from 96.0% to 72.0%, relieving egress buffer queue pressure.",
      "disclaimer": "SIMULATION ONLY — human review required. Does not modify physical infrastructure."
    }
  }
}
```

---

## 13. Requirements Traceability Table

| Mandatory Requirement (Section 1) | Architectural Implementation | Verification Evidence & Test |
|---|---|---|
| **1. At least 2 functional agents that really exchange information (build 5)** | Built 5 distinct agents (`performance_agent`, `infrastructure_agent`, `connectivity_agent`, `correlation_agent`, `reporting_agent`) communicating over async message bus. | `tests/test_agents.py`, `tests/test_correlation.py`, `demo.py` logs all 5 agent interactions. |
| **2. Documented, standardized JSON message protocol** | Version `1.0` JSON envelope with strict field types, UUIDs, enums, ISO-8601 timestamps, and Pydantic validation. Rejects unknown agents/types/versions. | [docs/AGENT_PROTOCOL.md](docs/AGENT_PROTOCOL.md), `tests/test_validators.py::test_agent_message_protocol_validation`. |
| **3. Central orchestrator that validates, dispatches, collects, routes, detects agent failure, produces final result** | `Orchestrator` manages lifecycle (`DX-YYYY-NNNN`), dispatches concurrently via `asyncio.gather`, enforces timeouts, handles degraded mode, and persists sessions. | `backend/app/orchestration/orchestrator.py`, `tests/test_scenarios.py` (Scenario 8 degraded agent test). |
| **4. Evidence-based root-cause diagnosis from telemetry, with alternatives and uncertainty** | `HypothesisScoringEngine` transparently ranks competing hypotheses, calculates confidence with penalties for close runner-ups (<0.08 margin = `ambiguous`), and records blind spots in `limitations`. | `backend/app/services/hypothesis_scoring.py`, `tests/test_correlation.py`. |
| **5. Structured JSON report in EXACT Section 6 format, plus Markdown report and dashboard** | `FinalDiagnosisReport` model serializes exact 10 Section 6 keys, enforces human-review suffix on actions, and restricts extra fields strictly to `extensions`. | `tests/test_section6_compliance.py` (validated against JSON Schema draft-07), `GET /api/diagnosis/{id}/report.md`. |
| **6. Input validation with clear errors (never silently ignore bad input)** | `validators.py` rejects invalid numerics (negatives, pct > 100), missing device IDs, orphan topology endpoints, and duplicate messages with standard error objects. | `tests/test_validators.py` (6 comprehensive validation tests). |
| **7. Sample scenarios, automated tests, and a one-command reproducible demo** | 8 realistic campus failure scenarios in `data/scenarios/`, 12 automated pytest unit/integration tests, and zero-dependency `python demo.py`. | `tests/test_scenarios.py` (all 8 pass in 0.39s), `demo.py` terminal walkthrough. |
| **8. Documentation & traceability table** | Complete documentation set: `ARCHITECTURE.md`, `AGENT_PROTOCOL.md`, `API.md`, `TESTING.md`, `DEMO.md`, `PRESENTATION.md`, `ADVANCED_FEATURES.md`, and requirements traceability table. | `docs/` directory and Section 13 of this README. |
| **9. Simulated remediation, human-in-the-loop wording, and persistence** | Every recommendation ends with *"Recommended action — human review required."*, remediation is simulation-only with disclaimer, and sessions persist to `data/sessions/`. | `backend/app/agents/reporting_agent.py`, `tests/test_section6_compliance.py`. |
| **10. Collaboration proof (Feature 1: Ablation)** | Quantitative proof that each agent shifts final diagnosis: re-runs pipeline with single agents removed in isolated sessions; measures confidence drop, root-cause shift, degradation, and lost evidence. | `services/ablation.py`, `tests/test_ablation.py`, `python demo.py --ablation`, `POST /api/diagnosis/{id}/ablation`. |
| **11. Not hardcoded (Feature 2: Fault Injection)** | Interactive chaos studio injecting arbitrary parameters with physical metric coupling and seeded PRNG into healthy base network; dynamic agents diagnose live. | `services/fault_injector.py`, `tests/test_fault_injection.py`, `python demo.py --inject congestion --seed 7`, `POST /api/inject/diagnose`. |
| **12. Reliability (Feature 3: Calibration & ECE)** | Evaluates Monte Carlo variants across 6 fault classes; computes Expected Calibration Error (<0.16 across 10 bins), reliability diagram, confusion matrix, and ambiguous abstain cap ($\le 0.65$). | `services/calibration.py`, `calibrate.py`, `tests/test_calibration.py`, `python demo.py --calibrate --runs 30`, `GET /api/calibration`. |
| **13. No unsupported claims (Feature 4: ClaimLedger)** | Atomic claim ledger where every sentence, metric, value, and device maps to an immutable message ID; 100% provenance coverage badge; Markdown footnote citations `[F1]`. | `models/claims.py`, `agents/reporting_agent.py`, `tests/test_traceability.py`, `python demo.py --trace`, `GET /api/diagnosis/{id}/claims`. |

---

## 14. Known Limitations & Future Scope
- **Telemetry Granularity**: Telemetry is currently ingested per poll interval; future iterations could support streaming telemetry via gRPC/gNMI.
- **Hardware Integration**: The system deliberately operates in simulation-only mode for remediation safety; future integrations could connect to NetBox or Cisco DNA Center via read-only APIs.
- **Active Probing**: Future agents could trigger synthetic ICMP/TWAMP network probes dynamically upon detecting ambiguities.

---

## 15. Safety & Simulation Disclaimer
> [!IMPORTANT]
> **Simulation and diagnostic recommendations only. No production network changes are performed.**
> The Signal Room strictly inspects and correlates telemetry. It has **no SSH credentials, no switch/router CLI execution privileges, no firewall rule manipulation, and no reboot capabilities**. All diagnostic findings and remediation proposals are advisory-only, generated for certified network engineers and NOC operators to review and authorize.
