# The Signal Room — Diagnostic Confidence Calculation Model
**Document Version 1.0 — Technical Engineering Reference**

---

## 1. Overview & Core Philosophy

In **The Signal Room**, diagnostic confidence is **never hardcoded** and never pegged to static consensus values (such as an unconditional 100% or 1.0). In real campus network operations, absolute certainty is rare due to measurement latency, telemetry jitter, asymmetric routing, and unmonitored Layer 2 boundaries.

Confidence is computed deterministically through a transparent, multi-factor scoring formula that balances:
1. **Evidence Strength ($E$)**: Magnitude and statistical significance of metric threshold breaches compared to historical baseline.
2. **Agent Agreement ($A$)**: Degree to which independent domain agents (Performance, Infrastructure, Connectivity) corroborate the same root-cause hypothesis.
3. **Evidence Coverage ($C$)**: Proportion of domain telemetry planes actively contributing to the analysis.
4. **Hypothesis Separation ($S$)**: Score delta between the leading hypothesis and the runner-up hypothesis.
5. **Deductions & Penalties**: Explicit downward adjustments for conflicting signals ($P_{\text{conflict}}$), missing metric telemetry ($P_{\text{missing}}$), and disabled or timed-out domain agents ($P_{\text{degraded}}$).

---

## 2. Mathematical Formulation

The base composite confidence score is calculated as:

$$\text{Confidence}_{\text{raw}} = 0.35 \cdot E + 0.25 \cdot A + 0.20 \cdot C + 0.20 \cdot S - P_{\text{conflict}} - P_{\text{missing}} - P_{\text{degraded}}$$

Where:

### 2.1 Evidence Strength ($E \in [0.0, 1.0]$)
Combines the volume of corroborating signal instances and the normalized hypothesis score:
$$E = \min\left(1.0, \, |\text{MatchedSignals}| \times 0.22 + \text{Score}_{\text{top}} \times 0.45\right)$$

### 2.2 Agent Agreement ($A \in [0.0, 1.0]$)
Measures inter-agent corroboration:
- $N_{\text{supporting}}$ is the count of domain agents whose telemetry directly supports the leading hypothesis.
- If all 3 domain agents corroborate (e.g. Performance detects 96% utilization, Infrastructure detects 15,790 buffer drops, Connectivity detects 12 nodes bottlenecked on the shared uplink), $A = 1.0$.
- If 2 agents corroborate, $A = 0.90$.
- If only 1 agent provides evidence, $A = \frac{1}{N_{\text{active}}} \approx 0.33 - 0.50$.

### 2.3 Evidence Coverage ($C \in [0.0, 1.0]$)
Evaluates telemetry plane completeness across the 3 core diagnostic domains:
$$C = \frac{\text{Active Domains Present}}{3.0}$$
Where the monitored domains are:
1. **Performance Plane**: Latency, jitter, throughput, packet loss.
2. **Infrastructure Plane**: Interface operational status, buffer queue drops, optical CRC framing errors, CPU/RAM utilization.
3. **Connectivity Plane**: Layer 2/3 topology graphs, blast radius isolation, shared uplink convergence.

### 2.4 Hypothesis Separation ($S \in [0.0, 1.0]$)
Quantifies margin of victory over competing hypotheses:
$$S = \max\left(0.0, \, \min\left(1.0, \, (\text{Score}_{\text{winner}} - \text{Score}_{\text{runner-up}}) \times 2.0\right)\right)$$
A large score separation indicates decisive convergence; a narrow separation indicates competing explanations.

---

## 3. Explicit Deductions & Penalties

| Penalty Factor | Condition | Deduction | Operational Rationale |
|---|---|---|---|
| **Conflict Penalty** ($P_{\text{conflict}}$) | Contradictory signals detected (e.g. packet loss without queue drops or CPU churn) | `-0.20` | Prevents the system from claiming high certainty when telemetry signals point in opposing directions. |
| **Missing Plane Penalty** ($P_{\text{missing}}$) | Domain agent telemetry omitted | `-0.10` per missing plane | Reflects information blindspots (e.g. missing infrastructure queue drop counters). |
| **Degraded Agent Penalty** ($P_{\text{degraded}}$) | Agent explicitly disabled in ablation or timed out | `-0.15` per degraded agent | Quantitatively penalizes diagnostic reliability when an agent fails to report. |

---

## 4. Status-Specific Clamping & Boundary Rules

Depending on the operational classification, final confidence is bounded within realistic operational windows:

### 4.1 Diagnosed Scenario (`status: "diagnosed"`)
$$\text{Confidence}_{\text{final}} = \text{round}\left(\min(0.96, \, \max(0.40, \, \text{Confidence}_{\text{raw}})), \, 2\right)$$
- The absolute maximum is capped at **0.96 (96%)**, enforcing humility in diagnostic recommendations.
- Flagship multi-agent congestion with 3-agent agreement achieves **0.90 – 0.95**.

### 4.2 Ambiguous Scenario (`status: "ambiguous"`)
$$\text{Confidence}_{\text{final}} = \text{round}\left(\min(0.50, \, \max(0.35, \, \text{Confidence}_{\text{raw}})), \, 2\right)$$
- Bounded to **0.35 – 0.50**.
- The system explicitly surfaces: *"Available evidence is insufficient to determine a unique root cause."*

### 4.3 Insufficient Evidence Scenario (`status: "insufficient_evidence"`)
$$\text{Confidence}_{\text{final}} = 0.15$$
- Fixed low confidence floor when mandatory metrics (packet loss, link utilization) are absent from raw telemetry.
- No root cause is fabricated; missing fields and required polling streams are reported.

### 4.4 Normal Network Operation (`status: "no_fault_detected"`)
$$\text{Cleanliness} = 1.0 - \max\left(\frac{\text{util}}{100}, \, \frac{\text{loss}}{10}, \, \frac{\text{lat}}{100}, \, \frac{\text{cpu}}{100}\right)$$
$$\text{Confidence}_{\text{final}} = \text{round}\left(\min(0.95, \, \max(0.70, \, 0.76 + 0.18 \cdot \text{Cleanliness} - P_{\text{degraded}})), \, 2\right)$$
- Confirms nominal state with high confidence (0.85 – 0.94) when all metrics sit well within baseline boundaries.

---

## 5. Verification & Proof of Collaboration (Ablation Test)

The dynamic formula is verified continuously through unit and integration tests (`tests/test_hackathon_hardening.py`):
1. **Full Run**: All 3 domain agents active $\rightarrow \text{Confidence} \approx 0.92$.
2. **Ablation Run**: Remove Performance Agent $\rightarrow \text{Confidence} \approx 0.65$ ($\Delta = -0.27$).
3. **Ablation Run**: Remove Infrastructure Agent $\rightarrow \text{Confidence} \approx 0.61$ ($\Delta = -0.31$).
4. **Conflicting Telemetry**: Packet loss present with 0 drops $\rightarrow \text{Status} = \text{AMBIGUOUS}$, $\text{Confidence} \approx 0.45$.
