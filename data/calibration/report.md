# Calibration & Reliability Report

**Generated:** `2026-10-31T21:22:09.263047Z`  
**Total Monte Carlo Runs:** `6`  
**Headline Metric:** `Accuracy 100.0% | ECE 0.178 | Correct conf: 82% vs Incorrect conf: 0% (Abstain rate: 16.7%)`

## Overall Metrics
- **Overall Accuracy:** `100.0%`
- **Expected Calibration Error (ECE):** `0.1780`
- **Mean Confidence on Correct Predictions:** `0.82`
- **Mean Confidence on Incorrect Predictions:** `0.00`
- **Safe Abstain / Ambiguity Capture Rate:** `16.7%`

## Per-Class Accuracy
| Fault Class | Accuracy |
|---|---|
| `normal` | 100.0% |
| `congestion` | 100.0% |
| `overload` | 100.0% |
| `interface_failure` | 100.0% |
| `crc_problem` | 100.0% |
| `ambiguous` | 100.0% |

## Reliability Diagram (10 Confidence Bins)
| Bin Range | Samples | Mean Conf | Empirical Acc | |Gap| |
|---|---|---|---|---|
| `0.0-0.1` | 0 | 0.05 | 0.00 | 0.00 |
| `0.1-0.2` | 0 | 0.15 | 0.00 | 0.00 |
| `0.2-0.3` | 0 | 0.25 | 0.00 | 0.00 |
| `0.3-0.4` | 1 | 0.35 | 1.00 | 0.65 |
| `0.4-0.5` | 0 | 0.45 | 0.00 | 0.00 |
| `0.5-0.6` | 0 | 0.55 | 0.00 | 0.00 |
| `0.6-0.7` | 0 | 0.65 | 0.00 | 0.00 |
| `0.7-0.8` | 0 | 0.75 | 0.00 | 0.00 |
| `0.8-0.9` | 1 | 0.86 | 1.00 | 0.14 |
| `0.9-1.0` | 4 | 0.93 | 1.00 | 0.07 |

## Confusion Matrix
| Ground Truth \ Pred | `normal` | `congestion` | `overload` | `interface_failure` | `crc_problem` | `ambiguous` |
|---|---|---|---|---|---|---|
| `normal` | 1 | 0 | 0 | 0 | 0 | 0 |
| `congestion` | 0 | 1 | 0 | 0 | 0 | 0 |
| `overload` | 0 | 0 | 1 | 0 | 0 | 0 |
| `interface_failure` | 0 | 0 | 0 | 1 | 0 | 0 |
| `crc_problem` | 0 | 0 | 0 | 0 | 1 | 0 |
| `ambiguous` | 0 | 0 | 0 | 0 | 0 | 1 |
