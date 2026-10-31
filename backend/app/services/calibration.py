import os
import json
import random
import copy
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.orchestration.orchestrator import orchestrator
from app.api.routes import load_default_topology, SCENARIOS_DIR
from app.models.diagnosis import DiagnosisStatus

CALIBRATION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/calibration"))
CALIBRATION_JSON = os.path.join(CALIBRATION_DIR, "report.json")
CALIBRATION_MD = os.path.join(CALIBRATION_DIR, "report.md")

FAULT_CLASSES = [
    "normal",
    "congestion",
    "overload",
    "interface_failure",
    "crc_problem",
    "ambiguous",
]

SCENARIO_MAP = {
    "normal": "01_normal_network.json",
    "congestion": "02_bandwidth_congestion.json",
    "overload": "03_device_overload.json",
    "interface_failure": "04_interface_failure.json",
    "crc_problem": "05_crc_error_degradation.json",
    "ambiguous": "06_ambiguous_fault.json",
}

CLASS_TO_HYPOTHESIS = {
    "normal": "Normal Network Operation (No Fault)",
    "congestion": "Bandwidth and Link Congestion",
    "overload": "Device Control Plane Overload (CPU/Memory)",
    "interface_failure": "Physical Interface or Link Down Failure",
    "crc_problem": "Physical Layer Cable / CRC Framing Degradation",
    "ambiguous": "Ambiguous Multi-Factor Degradation",
}


class ReliabilityBin(BaseModel):
    bin_index: int
    bin_range: str
    bin_lower: float
    bin_upper: float
    mean_confidence: float
    empirical_accuracy: float
    sample_count: int


class CalibrationReport(BaseModel):
    total_runs: int
    overall_accuracy: float
    expected_calibration_error: float
    mean_confidence_correct: float
    mean_confidence_incorrect: float
    ambiguous_rate: float
    abstain_rate: float
    per_class_accuracy: Dict[str, float]
    confusion_matrix: Dict[str, Dict[str, int]]
    reliability_diagram: List[ReliabilityBin]
    headline: str
    calibrated_at: str


class CalibrationEngine:
    """Evaluates and calibrates diagnostic confidence against ground-truth Monte Carlo variants."""

    @classmethod
    def generate_variant(
        cls,
        base_telemetry: List[Dict[str, Any]],
        ground_truth_class: str,
        rng: random.Random,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Generate a realistic randomized variant with noise, missing metrics, and occasional agent dropouts."""
        variant = copy.deepcopy(base_telemetry)
        disabled_agents = []

        # 10% chance of random agent dropout
        if rng.random() < 0.10 and ground_truth_class != "normal":
            possible_dropouts = ["connectivity_agent", "infrastructure_agent"]
            disabled_agents.append(rng.choice(possible_dropouts))

        for rec in variant:
            # Add subtle Gaussian noise to telemetry metrics
            if "latency_ms" in rec:
                rec["latency_ms"] = max(1.0, round(rec["latency_ms"] + rng.gauss(0, 2.5), 1))
            if "jitter_ms" in rec:
                rec["jitter_ms"] = max(0.1, round(rec["jitter_ms"] + rng.gauss(0, 1.2), 1))
            if "link_utilization_pct" in rec and rec.get("interface_status") != "down":
                rec["link_utilization_pct"] = min(99.0, max(5.0, round(rec["link_utilization_pct"] + rng.gauss(0, 2.0), 1)))
            if "packet_loss_pct" in rec and rec.get("interface_status") != "down" and rec["packet_loss_pct"] < 90.0:
                rec["packet_loss_pct"] = min(95.0, max(0.0, round(rec["packet_loss_pct"] + rng.gauss(0, 0.4), 2)))

            # Random 10% chance of dropping optional noise metrics
            if rng.random() < 0.10:
                rec.pop("jitter_ms", None)

        return variant, disabled_agents

    @classmethod
    async def run_calibration(
        cls,
        num_runs: int = 120,
        seed: int = 42,
    ) -> CalibrationReport:
        from datetime import datetime
        rng = random.Random(seed)
        topology = load_default_topology()

        # Load base scenarios
        base_scenarios: Dict[str, List[Dict[str, Any]]] = {}
        for cls_name, fname in SCENARIO_MAP.items():
            fpath = os.path.join(SCENARIOS_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                base_scenarios[cls_name] = json.load(f).get("telemetry", [])

        runs_per_class = max(1, num_runs // len(FAULT_CLASSES))
        eval_records: List[Dict[str, Any]] = []

        for gt_class in FAULT_CLASSES:
            base_telem = base_scenarios[gt_class]
            for run_i in range(runs_per_class):
                variant_telem, disabled = cls.generate_variant(base_telem, gt_class, rng)
                incident_id = f"INC-CALIB-{gt_class[:3].upper()}-{run_i:03d}"
                
                session_rec = await orchestrator.run_diagnostic_session(
                    telemetry_raw=variant_telem,
                    topology_raw=topology,
                    incident_id=incident_id,
                    disabled_agents=disabled,
                )
                rep = session_rec.final_report
                
                # Check prediction
                top_hyp = rep.suspected_root_cause
                if rep.extensions and rep.extensions.hypotheses_ranking:
                    top_hyp = rep.extensions.hypotheses_ranking[0].hypothesis

                # Determine correctness
                expected_hyp = CLASS_TO_HYPOTHESIS[gt_class]
                is_correct = False
                abstained = False

                if gt_class == "normal":
                    if rep.status == DiagnosisStatus.NO_FAULT_DETECTED or top_hyp == expected_hyp:
                        is_correct = True
                elif gt_class == "ambiguous":
                    if rep.status in (DiagnosisStatus.AMBIGUOUS, DiagnosisStatus.INSUFFICIENT_DATA) or rep.confidence <= 0.65 or "ambiguous" in top_hyp.lower():
                        is_correct = True
                        abstained = True
                else:
                    if top_hyp == expected_hyp and rep.status == DiagnosisStatus.DIAGNOSED:
                        is_correct = True
                    elif rep.status in (DiagnosisStatus.AMBIGUOUS, DiagnosisStatus.INSUFFICIENT_DATA):
                        abstained = True

                conf = round(float(rep.confidence), 2)
                eval_records.append(
                    {
                        "ground_truth": gt_class,
                        "expected_hypothesis": expected_hyp,
                        "predicted_hypothesis": top_hyp,
                        "status": rep.status.value,
                        "confidence": conf,
                        "is_correct": is_correct,
                        "abstained": abstained,
                    }
                )

        # 1. Overall Accuracy
        total = len(eval_records)
        correct_count = sum(1 for r in eval_records if r["is_correct"])
        overall_acc = round(correct_count / total, 3)

        # 2. Per-Class Accuracy
        class_acc: Dict[str, float] = {}
        confusion: Dict[str, Dict[str, int]] = {gt: {pred: 0 for pred in FAULT_CLASSES} for gt in FAULT_CLASSES}

        hyp_to_class = {h: c for c, h in CLASS_TO_HYPOTHESIS.items()}

        for r in eval_records:
            gt = r["ground_truth"]
            pred_hyp = r["predicted_hypothesis"]
            pred_cls = hyp_to_class.get(pred_hyp, "ambiguous")
            if r["status"] in ("ambiguous", "insufficient_data"):
                pred_cls = "ambiguous"
            confusion[gt][pred_cls] = confusion[gt].get(pred_cls, 0) + 1

        for gt in FAULT_CLASSES:
            gt_records = [r for r in eval_records if r["ground_truth"] == gt]
            gt_correct = sum(1 for r in gt_records if r["is_correct"])
            class_acc[gt] = round(gt_correct / len(gt_records), 3) if gt_records else 0.0

        # 3. Expected Calibration Error (ECE) across 10 bins
        bins = []
        num_bins = 10
        total_ece = 0.0

        for b in range(num_bins):
            b_lower = b / num_bins
            b_upper = (b + 1) / num_bins
            bin_items = [
                r for r in eval_records
                if (b_lower <= r["confidence"] < b_upper if b < num_bins - 1 else b_lower <= r["confidence"] <= b_upper)
            ]
            
            count = len(bin_items)
            if count > 0:
                mean_conf = round(sum(r["confidence"] for r in bin_items) / count, 3)
                emp_acc = round(sum(1 for r in bin_items if r["is_correct"]) / count, 3)
                bin_err = abs(emp_acc - mean_conf)
                total_ece += (count / total) * bin_err
            else:
                mean_conf = round((b_lower + b_upper) / 2.0, 3)
                emp_acc = 0.0

            bins.append(
                ReliabilityBin(
                    bin_index=b + 1,
                    bin_range=f"{b_lower:.1f}-{b_upper:.1f}",
                    bin_lower=b_lower,
                    bin_upper=b_upper,
                    mean_confidence=mean_conf,
                    empirical_accuracy=emp_acc,
                    sample_count=count,
                )
            )

        ece = round(total_ece, 3)

        # 4. Confidence on Correct vs Incorrect
        correct_records = [r for r in eval_records if r["is_correct"]]
        incorrect_records = [r for r in eval_records if not r["is_correct"]]
        mean_conf_corr = round(sum(r["confidence"] for r in correct_records) / len(correct_records), 3) if correct_records else 0.0
        mean_conf_inc = round(sum(r["confidence"] for r in incorrect_records) / len(incorrect_records), 3) if incorrect_records else 0.0

        # 5. Abstain & Ambiguous Rates
        abstained_count = sum(1 for r in eval_records if r["abstained"])
        abstain_rate = round(abstained_count / total, 3)
        ambiguous_cases = [r for r in eval_records if r["ground_truth"] == "ambiguous"]
        ambiguous_rate = round(sum(1 for r in ambiguous_cases if r["is_correct"]) / len(ambiguous_cases), 3) if ambiguous_cases else 1.0

        headline = (
            f"Accuracy {overall_acc * 100:.1f}% | ECE {ece:.3f} | Correct conf: {mean_conf_corr * 100:.0f}% vs "
            f"Incorrect conf: {mean_conf_inc * 100:.0f}% (Abstain rate: {abstain_rate * 100:.1f}%)"
        )

        now_str = datetime.utcnow().isoformat() + "Z"

        report = CalibrationReport(
            total_runs=total,
            overall_accuracy=overall_acc,
            expected_calibration_error=ece,
            mean_confidence_correct=mean_conf_corr,
            mean_confidence_incorrect=mean_conf_inc,
            ambiguous_rate=ambiguous_rate,
            abstain_rate=abstain_rate,
            per_class_accuracy=class_acc,
            confusion_matrix=confusion,
            reliability_diagram=bins,
            headline=headline,
            calibrated_at=now_str,
        )

        # Persist report files
        cls.save_reports(report)
        return report

    @classmethod
    def save_reports(cls, report: CalibrationReport) -> None:
        os.makedirs(CALIBRATION_DIR, exist_ok=True)
        # JSON
        with open(CALIBRATION_JSON, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2)

        # Markdown
        md = []
        md.append("# Calibration & Reliability Report\n")
        md.append(f"**Generated:** `{report.calibrated_at}`  ")
        md.append(f"**Total Monte Carlo Runs:** `{report.total_runs}`  ")
        md.append(f"**Headline Metric:** `{report.headline}`\n")

        md.append("## Overall Metrics")
        md.append(f"- **Overall Accuracy:** `{report.overall_accuracy * 100:.1f}%`")
        md.append(f"- **Expected Calibration Error (ECE):** `{report.expected_calibration_error:.4f}`")
        md.append(f"- **Mean Confidence on Correct Predictions:** `{report.mean_confidence_correct:.2f}`")
        md.append(f"- **Mean Confidence on Incorrect Predictions:** `{report.mean_confidence_incorrect:.2f}`")
        md.append(f"- **Safe Abstain / Ambiguity Capture Rate:** `{report.abstain_rate * 100:.1f}%`\n")

        md.append("## Per-Class Accuracy")
        md.append("| Fault Class | Accuracy |")
        md.append("|---|---|")
        for cls_name, acc in report.per_class_accuracy.items():
            md.append(f"| `{cls_name}` | {acc * 100:.1f}% |")
        md.append("")

        md.append("## Reliability Diagram (10 Confidence Bins)")
        md.append("| Bin Range | Samples | Mean Conf | Empirical Acc | |Gap| |")
        md.append("|---|---|---|---|---|")
        for b in report.reliability_diagram:
            gap = abs(b.empirical_accuracy - b.mean_confidence) if b.sample_count > 0 else 0.0
            md.append(f"| `{b.bin_range}` | {b.sample_count} | {b.mean_confidence:.2f} | {b.empirical_accuracy:.2f} | {gap:.2f} |")
        md.append("")

        md.append("## Confusion Matrix")
        headers = ["Ground Truth \\ Pred"] + [f"`{c}`" for c in FAULT_CLASSES]
        md.append("| " + " | ".join(headers) + " |")
        md.append("|" + "---|"*len(headers))
        for gt in FAULT_CLASSES:
            row = [f"`{gt}`"] + [str(report.confusion_matrix.get(gt, {}).get(p, 0)) for p in FAULT_CLASSES]
            md.append("| " + " | ".join(row) + " |")
        md.append("")

        with open(CALIBRATION_MD, "w", encoding="utf-8") as f:
            f.write("\n".join(md))

    @classmethod
    def get_latest_report(cls) -> Optional[Dict[str, Any]]:
        if os.path.exists(CALIBRATION_JSON):
            try:
                with open(CALIBRATION_JSON, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None
