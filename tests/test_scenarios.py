import os
import json
import pytest
from app.orchestration.orchestrator import Orchestrator
from app.api.routes import SCENARIOS_DIR, load_default_topology
from app.models.diagnosis import DiagnosisStatus


@pytest.mark.asyncio
async def test_all_scenarios_execute_and_produce_valid_diagnosis():
    orch = Orchestrator()
    topology = load_default_topology()

    scenario_files = sorted([f for f in os.listdir(SCENARIOS_DIR) if f.endswith(".json")])
    assert len(scenario_files) >= 8, f"Expected 8 scenarios, found {len(scenario_files)}"

    for sfile in scenario_files:
        fpath = os.path.join(SCENARIOS_DIR, sfile)
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        telemetry = data["telemetry"]
        incident_id = data.get("incident_id")
        disabled = data.get("disabled_agents", [])

        rec = await orch.run_diagnostic_session(
            telemetry_raw=telemetry,
            topology_raw=topology,
            incident_id=incident_id,
            disabled_agents=disabled,
        )

        assert rec.final_report is not None
        assert rec.final_report.confidence > 0.0
        assert rec.final_report.incident_id == incident_id

        # Check scenario-specific expectations
        sname = data.get("scenario_id")
        if "01_normal" in sname:
            assert rec.final_report.status == DiagnosisStatus.NO_FAULT_DETECTED
        elif "02_congestion" in sname:
            assert "congestion" in rec.final_report.suspected_root_cause.lower()
        elif "03_overload" in sname:
            assert "resource" in rec.final_report.suspected_root_cause.lower() or "overload" in rec.final_report.suspected_root_cause.lower()
        elif "04_interface" in sname:
            assert "interface" in rec.final_report.suspected_root_cause.lower() or "down" in rec.final_report.suspected_root_cause.lower()
        elif "05_crc" in sname:
            assert "crc" in rec.final_report.suspected_root_cause.lower() or "framing" in rec.final_report.suspected_root_cause.lower()
        elif "06_ambiguous" in sname:
            assert rec.final_report.status in (DiagnosisStatus.AMBIGUOUS, DiagnosisStatus.DIAGNOSED)
        elif "07_hackathon" in sname:
            assert "congestion" in rec.final_report.suspected_root_cause.lower()
            assert len(rec.final_report.affected_devices) >= 1
        elif "08_degraded" in sname:
            assert any("infrastructure_agent" in lim for lim in rec.final_report.limitations)
        elif "09_insufficient" in sname:
            assert rec.final_report.status == DiagnosisStatus.INSUFFICIENT_EVIDENCE
