# REST & Streaming API Documentation

## Base URL
`http://localhost:8000/api`

---

## 1. System Endpoints

### `GET /api/health`
Checks backend system availability and active agent status.
```json
{
  "status": "healthy",
  "service": "Multi-Agent Network Fault Diagnosis System",
  "version": "1.0.0",
  "active_agents": [
    "performance_agent",
    "infrastructure_agent",
    "connectivity_agent",
    "correlation_agent",
    "reporting_agent"
  ]
}
```

### `GET /api/topology`
Returns the complete IIT campus topology nodes and links.

---

## 2. Telemetry Ingestion

### `POST /api/telemetry`
Validates and accepts batches of raw telemetry records.
**Request Body:**
```json
{
  "records": [
    {
      "device_id": "HOSTEL_CORE_SW_01",
      "device_type": "switch",
      "timestamp": "2026-10-31T21:00:00Z",
      "latency_ms": 145.0,
      "jitter_ms": 38.0,
      "packet_loss_pct": 8.2,
      "link_utilization_pct": 96.0,
      "cpu_utilization_pct": 62.0,
      "memory_utilization_pct": 58.0,
      "queue_drops": 14230,
      "crc_errors": 4
    }
  ]
}
```

---

## 3. Diagnostic Orchestration

### `POST /api/diagnose`
Runs a full autonomous diagnostic session across all agents.
**Request Body:**
```json
{
  "telemetry": [...],
  "topology": {...},
  "incident_id": "INC-8832",
  "disabled_agents": []
}
```
**Response:** Strict Section 6 JSON report with extensions.

---

## 4. Preconfigured Scenarios

### `GET /api/scenarios`
Lists all 8 pre-loaded campus failure scenarios.

### `POST /api/scenarios/{name}/run`
Executes a specific scenario by name (e.g., `07_hackathon_demo.json`) with optional agent disabling.
**Request Body:**
```json
{
  "disabled_agents": ["infrastructure_agent"]
}
```

---

## 5. Session Inspection & Artifacts

### `GET /api/diagnosis/{id}`
Fetches the Section 6 JSON report by `session_id` (`DX-2026-0001`) or `incident_id` (`INC-8832`).

### `GET /api/messages`
Retrieves messages for the latest diagnostic session, or for a specific session via `?session_id=DX-...`.

### `GET /api/findings`
Retrieves domain agent findings for the latest diagnostic session, or for a specific session via `?session_id=DX-...`.

### `GET /api/diagnosis/{id}/messages`
Retrieves all protocol messages exchanged during the diagnostic session.

### `GET /api/diagnosis/{id}/findings`
Retrieves domain agent findings and cross-query exchanges.

### `GET /api/diagnosis/{id}/report.md`
Returns the executive Markdown diagnostic report.

### `GET /api/diagnosis/{id}/stream`
Server-Sent Events (SSE) live message stream for real-time frontend visualization.

---

## 6. Advanced Features Endpoints

### 6.1 Agent Ablation Analysis
- `POST /api/diagnosis/{id}/ablation`: Executes concurrent isolated ablation configurations and computes per-agent contribution deltas.
- `GET /api/diagnosis/{id}/ablation`: Retrieves cached ablation report for the session.

### 6.2 Fault Injection Studio
- `GET /api/inject/presets`: Lists pre-configured fault presets (`congestion`, `overload`, `interface_failure`, `crc_problem`).
- `POST /api/inject`: Generates physically-coupled synthetic telemetry from base network and injection parameters.
- `POST /api/inject/diagnose`: Injects faults and autonomously runs the full multi-agent diagnostic pipeline.

### 6.3 Calibrated Confidence
- `GET /api/calibration`: Returns the latest Monte Carlo calibration benchmark report (accuracy, ECE, reliability diagram, confusion matrix).
- `POST /api/calibration/run?runs=60&seed=42`: Re-runs the calibration evaluation across Monte Carlo variants.

### 6.4 ClaimLedger & Traceability
- `GET /api/diagnosis/{id}/claims`: Returns the complete atomic `ClaimLedger` with coverage percentage and message provenance.
- `GET /api/diagnosis/{id}/claims/{claim_id}`: Retrieves details and source message citations for an individual claim.

