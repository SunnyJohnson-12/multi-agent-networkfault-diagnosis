import pytest
import os
from fastapi.testclient import TestClient

from app.main import app
from app.services.calibration import CalibrationEngine, CALIBRATION_JSON

client = TestClient(app)


def test_calibration_endpoint_returns_valid_structure():
    resp = client.get("/api/calibration")
    assert resp.status_code == 200
    report = resp.json()

    assert "overall_accuracy" in report
    assert "expected_calibration_error" in report
    assert "reliability_diagram" in report
    assert "confusion_matrix" in report
    assert len(report["reliability_diagram"]) == 10
    assert report["overall_accuracy"] >= 0.85


def test_calibration_mean_confidence_separation():
    """Verify that correct answers have higher average confidence than incorrect ones."""
    resp = client.get("/api/calibration")
    assert resp.status_code == 200
    report = resp.json()

    assert report["mean_confidence_correct"] > report["mean_confidence_incorrect"]
    # Incorrect predictions should be uncertain
    assert report["mean_confidence_incorrect"] < 0.70


def test_ambiguous_scenario_confidence_cap():
    """Verify that ambiguous multi-factor scenario does not produce overconfident diagnosis (> 0.70)."""
    resp = client.post("/api/scenarios/06_ambiguous_fault.json/run")
    assert resp.status_code == 200
    report = resp.json()

    assert report["confidence"] <= 0.70
