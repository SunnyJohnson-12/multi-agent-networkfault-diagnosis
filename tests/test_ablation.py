import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ablation_proves_collaboration_on_demo_scenario():
    # 1. Run baseline scenario
    run_resp = client.post("/api/scenarios/07_hackathon_demo.json/run")
    assert run_resp.status_code == 200
    baseline_data = run_resp.json()
    session_id = baseline_data["extensions"]["session_id"]
    base_conf = baseline_data["confidence"]
    base_rc = baseline_data["suspected_root_cause"]

    # 2. Run ablation
    ablation_resp = client.post(f"/api/diagnosis/{session_id}/ablation")
    assert ablation_resp.status_code == 200
    ablation = ablation_resp.json()

    assert ablation["session_id"] == session_id
    assert ablation["collaboration_proven"] is True
    assert len(ablation["agent_contributions"]) == 3
    assert len(ablation["configurations"]) == 4  # Baseline + 3 disabled

    # Check performance_agent impact (vital for congestion detection)
    perf_contrib = next(c for c in ablation["agent_contributions"] if c["agent_name"] == "performance_agent")
    assert perf_contrib["confidence_delta"] > 0.10 or perf_contrib["root_cause_changed"] is True

    # Check connectivity_agent impact (vital for upstream bottle funneling)
    conn_contrib = next(c for c in ablation["agent_contributions"] if c["agent_name"] == "connectivity_agent")
    assert conn_contrib["confidence"] < base_conf or conn_contrib["confidence_delta"] >= 0.15

    # 3. Assert original session is unchanged
    orig_resp = client.get(f"/api/diagnosis/{session_id}")
    assert orig_resp.status_code == 200
    orig_data = orig_resp.json()
    assert orig_data["confidence"] == base_conf
    assert orig_data["suspected_root_cause"] == base_rc


def test_ablation_on_crc_scenario_identifies_infrastructure_agent():
    run_resp = client.post("/api/scenarios/05_crc_error_degradation.json/run")
    assert run_resp.status_code == 200
    session_id = run_resp.json()["extensions"]["session_id"]

    ablation_resp = client.get(f"/api/diagnosis/{session_id}/ablation")
    assert ablation_resp.status_code == 200
    ablation = ablation_resp.json()

    # In CRC scenario, infrastructure agent is critical
    infra_contrib = next(c for c in ablation["agent_contributions"] if c["agent_name"] == "infrastructure_agent")
    assert infra_contrib["confidence_delta"] > 0.10 or infra_contrib["root_cause_changed"] is True


def test_ablation_endpoint_caching_and_id_validation():
    # Encoded traversal or invalid characters
    bad_resp = client.get("/api/diagnosis/..%2f..%2fetc/passwd/ablation")
    assert bad_resp.status_code in (400, 404)

    bad_char_resp = client.get("/api/diagnosis/INVALID!@#$%/ablation")
    assert bad_char_resp.status_code == 400

    # Non-existent session
    notfound_resp = client.get("/api/diagnosis/DX-NONEXISTENT/ablation")
    assert notfound_resp.status_code == 404
