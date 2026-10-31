# Hackathon Pitch Script & Judge Q&A Guide

## 1. 3-Minute Live Demo Flow for Judges

Follow this exact 5-step sequence during the 3-minute hackathon evaluation.

### Step 1: Run the Demo Scenario (0:00 – 0:45)
- **Action**: Select `07_hackathon_demo.json` and click **"Run Diagnostic Protocol"** (or in terminal: `python demo.py`).
- **Narration**:
  > *"Judges, when 12 access switches and dorm APs start dropping packets in an enterprise campus network like IIT, NOC engineers are flooded with noisy alerts. Is it a fiber cut? A DDoS attack? A dead switch? Or buffer saturation?
  >
  > In The Signal Room, 5 autonomous specialized agents collaborate over a standardized JSON protocol (schema version 1.0). In milliseconds, they detect the anomaly, exchange cross-query clarification messages over the Agent Wire, converge hypotheses on the Hypothesis Race, and isolate the true root cause: severe uplink congestion and egress buffer saturation on `HOSTEL_CORE_SW_01` with 100% confidence."*

### Step 2: Open the Collaboration Proof Panel (0:45 – 1:15)
- **Action**: Click the **"Collaboration Proof"** tab (or in terminal: `python demo.py --ablation`).
- **Narration**:
  > *"When a judge asks: 'Is this real multi-agent collaboration, or just parallel scripts?', we don't just say yes—we mathematically prove it with **Agent Ablation Analysis**.
  >
  > Our ablation engine re-runs the entire pipeline in isolated concurrent sessions removing one agent at a time. Look at the delta matrix: without `performance_agent`, confidence plummets from 100% to 25%, and the diagnosis degrades into `ambiguous`. Without `infrastructure_agent`, queue drop evidence is lost and confidence drops by 25%. Every single agent provides non-redundant signal that directly shapes the consensus diagnosis."*

### Step 3: Inject a Fault Live in the Chaos Panel (1:15 – 1:55)
- **Action**: Switch to the **"Chaos Studio"** tab (or in terminal: `python demo.py --inject congestion --seed 7`). Move the utilization slider to 96%, queue drops to 12,500, or click the **"Congestion"** preset button, then click **"Inject & Run Autonomous Diagnosis"**.
- **Narration**:
  > *"When someone wonders: 'Is this hardcoded to canned JSON files?', we hand them the wheel in our **Fault Injection Studio**.
  >
  > Here, we start with a 100% clean, healthy campus network. I can choose any real device from our campus topology, inject custom utilization, packet loss, or port downs with physical metric coupling and seeded PRNG reproducibility. Notice the 'SIMULATED TELEMETRY' badge. The agents run completely fresh without knowing any expected outcome, analyze the telemetry, and autonomously isolate the injected fault in under 300 milliseconds."*

### Step 4: Show the Reliability Panel (1:55 – 2:25)
- **Action**: Switch to the **"Reliability & ECE"** tab (or in terminal: `python demo.py --calibrate --runs 30`).
- **Narration**:
  > *"Can an engineer actually trust these confidence numbers? In mission-critical NOC operations, overconfidence is catastrophic.
  >
  > In this **Reliability Panel**, we run extensive Monte Carlo evaluation across noisy variants. Notice our Expected Calibration Error (ECE) is 0.148 across 10 bins. Most importantly: when the system is right, average confidence is 85%; when it makes a mistake, average confidence is 0% to 35%—a massive separation. Furthermore, when presented with ambiguous or conflicting signals, it refuses to hallucinate: it appropriately abstains with an ambiguous status and capped confidence."*

### Step 5: Click a Report Claim and Show Its Trace (2:25 – 3:00)
- **Action**: Switch to **"Section 6 Report"** $\to$ click the **"Claim Ledger"** tab (or in terminal: `python demo.py --trace`). Click claim `CLM-001` or `CLM-002`.
- **Narration**:
  > *"Finally, we achieve **100% Evidence-to-Claim Traceability**.
  >
  > Every single assertion in our Section 6 report carries an atomic claim ID and footnote citation `[F1]`, `[F2]`. When I click this claim, the system highlights the exact protocol message ID on the Agent Wire, the telemetry measurement on the Evidence Board, and the physical switch on the Topology Map. If an optional LLM tries to hallucinate an invented number or device, our anti-hallucination guard immediately rejects it and falls back to our verified deterministic template.
  >
  > Zero unsupported claims. Zero AI hallucinations. Fully auditable."*

---

## 2. Anticipated Judge Questions & Defenses

### Q1: "Where is the multi-agent collaboration? Couldn't a single script do this?"
**Defense:**
> "Open the **Collaboration Proof** tab (`python demo.py --ablation`). Disabling the Performance Agent causes an empirical 75% confidence drop and degrades the incident from `diagnosed` to `ambiguous`. Disabling the Infrastructure Agent loses all hardware queue drop evidence.
>
> Furthermore, in the Agent Wire, the Correlation Agent autonomously initiates a `clarification_request` to the Connectivity Agent to test shared topology dependencies. The Connectivity Agent executes graph traversal and confirms a 100% shared uplink bottleneck through `HOSTEL_CORE_SW_01`. The diagnosis is an emergent consensus of distinct domain perspectives."

### Q2: "How do you prove nothing is hardcoded?"
**Defense:**
> "Open **Chaos Studio** (`python demo.py --inject overload --seed 42`). We can inject arbitrary telemetry onto any campus node with user-selected utilization, packet loss, or CPU levels. In tests, we ran a continuous monotonicity sweep: gradually increasing utilization on a link causes the congestion hypothesis score to increase monotonically from 0.0 to 1.0 while transitioning from `no_fault_detected` to `diagnosed`."

### Q3: "How do you know the 85% confidence score is calibrated and not arbitrary?"
**Defense:**
> "We measure Expected Calibration Error (ECE) across 10 empirical probability bins using Monte Carlo variants (`python demo.py --calibrate`). Our ECE is under 0.16. When the model errs, average confidence is 35% or lower. In ambiguous scenarios, confidence is mathematically capped at 0.65."

### Q4: "What if an LLM is enabled and hallucinates an IP address or metric?"
**Defense:**
> "Our Claim Ledger requires 100% provenance coverage. Every device and metric in the final report must resolve to an immutable message ID in the session bus. If an LLM response contains an unregistered device or value, our validator flags it as unsupported, logs a rejection, and immediately triggers an automatic fallback to the verified template generator."
