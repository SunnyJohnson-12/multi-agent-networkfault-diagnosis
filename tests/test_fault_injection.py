import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_presets_lead_to_expected_fault_classes():
    # 1. Congestion preset
    resp = client.post("/api/inject/diagnose", json={"preset": "congestion", "seed": 42})
    assert resp.status_code == 200
    report = resp.json()
    assert report["status"] == "diagnosed"
    assert "congestion" in report["suspected_root_cause"].lower()
    assert report["confidence"] >= 0.80
    assert report["extensions"]["simulated_telemetry"] is True

    # 2. Overload preset
    resp = client.post("/api/inject/diagnose", json={"preset": "overload", "seed": 42})
    assert resp.status_code == 200
    report = resp.json()
    assert report["status"] == "diagnosed"
    assert any(term in report["suspected_root_cause"].lower() for term in ("overload", "cpu", "resource", "exhaustion"))

    # 3. Interface failure preset
    resp = client.post("/api/inject/diagnose", json={"preset": "interface_failure", "seed": 42})
    assert resp.status_code == 200
    report = resp.json()
    assert report["status"] == "diagnosed"
    assert any(term in report["suspected_root_cause"].lower() for term in ("interface", "down", "link failure"))

    # 4. CRC framing degradation preset
    resp = client.post("/api/inject/diagnose", json={"preset": "crc_problem", "seed": 42})
    assert resp.status_code == 200
    report = resp.json()
    assert report["status"] == "diagnosed"
    assert any(term in report["suspected_root_cause"].lower() for term in ("crc", "cable", "physical layer"))


def test_seed_gives_identical_telemetry_and_diagnosis():
    payload = {
        "preset": "congestion",
        "seed": 999,
        "injections": [
            {"target_device_id": "HOSTEL_CORE_SW_01", "metric": "link_utilization_pct", "value": 94.5}
        ],
    }
    resp1 = client.post("/api/inject/diagnose", json=payload)
    resp2 = client.post("/api/inject/diagnose", json=payload)

    assert resp1.status_code == 200
    assert resp2.status_code == 200

    r1 = resp1.json()
    r2 = resp2.json()

    assert r1["confidence"] == r2["confidence"]
    assert r1["suspected_root_cause"] == r2["suspected_root_cause"]
    assert len(r1["supporting_evidence"]) == len(r2["supporting_evidence"])


def test_invalid_target_and_bounds_rejected():
    # Unknown target
    resp = client.post(
        "/api/inject",
        json={
            "injections": [{"target_device_id": "ROGUE_DEVICE_999", "metric": "link_utilization_pct", "value": 50.0}]
        },
    )
    assert resp.status_code == 400
    assert "INVALID_TARGET_DEVICE" in resp.text

    # Out of bounds percentage
    resp = client.post(
        "/api/inject",
        json={
            "injections": [{"target_device_id": "HOSTEL_CORE_SW_01", "metric": "link_utilization_pct", "value": 150.0}]
        },
    )
    assert resp.status_code == 400
    assert "INVALID_METRIC_BOUNDS" in resp.text


def test_monotonic_utilization_sweep():
    """Gradually raise utilization on a core switch and assert congestion hypothesis score is monotonic non-decreasing."""
    utilizations = [20.0, 45.0, 75.0, 85.0, 96.0]
    scores = []
    statuses = []

    for util in utilizations:
        resp = client.post(
            "/api/inject/diagnose",
            json={
                "injections": [
                    {"target_device_id": "HOSTEL_CORE_SW_01", "metric": "link_utilization_pct", "value": util}
                ],
                "couple_metrics": True,
                "seed": 777,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        statuses.append(data["status"])
        
        # Find congestion score
        hypotheses = data["extensions"]["hypotheses_ranking"]
        congestion_score = next((h["score"] for h in hypotheses if "Congestion" in h["hypothesis"]), 0.05)
        scores.append(congestion_score)

    # Monotonic non-decreasing check
    for i in range(len(scores) - 1):
        assert scores[i] <= scores[i + 1], f"Score drop from {scores[i]} to {scores[i+1]} at util {utilizations[i+1]}"

    # Transitions from healthy to diagnosed
    assert statuses[0] == "no_fault_detected"
    assert statuses[-1] == "diagnosed"
