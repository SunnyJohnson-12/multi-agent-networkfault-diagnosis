# Automated Testing Suite & Verification Guide

## 1. Overview
The testing suite covers all functional requirements: telemetry input validation, protocol schema enforcement, individual agent analysis, correlation logic, Section 6 JSON compliance, agent degradation resilience, security defenses, and all four Advanced Features (Ablation, Fault Injection, Calibration, and Traceability).

---

## 2. Running Automated Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Execute all tests with detailed verbosity
pytest -v

# Run with coverage report
pytest --cov=app tests/

# Execute individual test suites
pytest -v tests/test_ablation.py
pytest -v tests/test_fault_injection.py
pytest -v tests/test_calibration.py
pytest -v tests/test_traceability.py
pytest -v tests/security/test_security_defenses.py
```

---

## 3. Test Coverage Matrix

| Test Module | Coverage Focus | Key Invariant Verified |
|---|---|---|
| `tests/test_validators.py` | Input validation, bounds, schema version | Rejects out-of-range metrics (pct > 100, negative latency), orphan links, and schema mismatches. |
| `tests/test_agents.py` | Performance, Infrastructure, Connectivity agents | Asserts accurate domain threshold detection, queue drop parsing, CRC error logs, and blast radius calculation. |
| `tests/test_correlation.py` | Multi-agent collaboration proof | Proves removing an agent drops confidence and adds limitation flags. |
| `tests/test_section6_compliance.py` | Strict Section 6 JSON Schema | Uses `jsonschema.validate` to confirm all 10 mandatory keys exist and every recommendation ends with *"Recommended action — human review required."* |
| `tests/test_scenarios.py` | All 8 campus scenarios | Asserts that expected root causes are **derived dynamically by agents** across all 8 failure scenarios. |
| `tests/test_ablation.py` | Feature 1: Agent Ablation Analysis | Asserts removing most relevant agent changes confidence or status; verifies original session is never mutated; tests caching and input sanitization. |
| `tests/test_fault_injection.py` | Feature 2: Fault Injection Studio | Asserts each preset leads to its expected fault class; verifies identical seed gives identical telemetry and diagnosis; rejects invalid targets; executes monotonic utilization sweep. |
| `tests/test_calibration.py` | Feature 3: Calibrated Confidence | Asserts mean confidence separation (correct vs incorrect); verifies ambiguous scenario confidence cap ($\le 0.65$); tests `/api/calibration` endpoint. |
| `tests/test_traceability.py` | Feature 4: ClaimLedger & Traceability | Asserts 100% provenance coverage across all scenarios; verifies claim sources exist in session messages; tests rejection of unsupported claims; verifies Markdown footnote citations `[F1]`. |
| `tests/security/test_security_defenses.py` | Security Defenses & Red-Team Audit | Verifies path traversal defense, NaN/Inf rejection, prompt injection resilience, simulated remediation safety, message spoofing rejection, payload size bounding, and secret leakage prevention. |

---

## 4. Verification Results
```
tests/security/test_security_defenses.py ................                [ 37%]
tests/test_ablation.py ...                                               [ 44%]
tests/test_agents.py ...                                                 [ 51%]
tests/test_calibration.py ...                                            [ 58%]
tests/test_correlation.py .                                              [ 60%]
tests/test_fault_injection.py ....                                       [ 69%]
tests/test_scenarios.py .                                                [ 74%]
tests/test_section6_compliance.py .                                      [ 76%]
tests/test_traceability.py .....                                         [ 88%]
tests/test_validators.py ......                                          [100%]

============================== 43 passed in 0.98s ==============================
```
