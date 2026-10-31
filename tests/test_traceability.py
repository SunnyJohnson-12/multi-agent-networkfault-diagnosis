import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.claims import ClaimLedger, ClaimSource
from app.orchestration.orchestrator import orchestrator
from app.api.routes import load_default_topology, SCENARIOS_DIR
import json
import os

client = TestClient(app)


def test_every_scenario_has_100_percent_traceability_coverage():
    """Verify that every standard scenario generates a report with 100% claim coverage."""
    for fname in sorted(os.listdir(SCENARIOS_DIR)):
        if not fname.endswith(".json"):
            continue
        response = client.post(f"/api/scenarios/{fname}/run")
        assert response.status_code == 200, f"Scenario {fname} failed execution"
        data = response.json()
        
        ext = data.get("extensions", {})
        trace = ext.get("traceability", {})
        claims = ext.get("claim_ledger", [])
        
        assert len(claims) > 0, f"Scenario {fname} has no claims"
        assert trace.get("coverage_pct") == 100.0, f"Scenario {fname} coverage is {trace.get('coverage_pct')}%"
        assert trace.get("unsupported_claims") == 0, f"Scenario {fname} has unsupported claims"

        # Check that each claim has valid sources
        for claim in claims:
            assert len(claim["sources"]) > 0
            for src in claim["sources"]:
                assert src["message_id"] is not None
                assert src["source_agent"] is not None


def test_claim_sources_exist_in_session_messages():
    """Verify that every source message_id cited by a claim exists in the session message log."""
    response = client.post("/api/scenarios/07_hackathon_demo.json/run")
    assert response.status_code == 200
    report = response.json()
    
    session_id = report["extensions"]["session_id"]
    
    # Fetch session messages
    msg_resp = client.get(f"/api/diagnosis/{session_id}/messages")
    assert msg_resp.status_code == 200
    messages = msg_resp.json()["messages"]
    message_ids = {m["message_id"] for m in messages}
    
    # Fetch claims
    claims_resp = client.get(f"/api/diagnosis/{session_id}/claims")
    assert claims_resp.status_code == 200
    claims = claims_resp.json()["claims"]
    
    for c in claims:
        for s in c["sources"]:
            assert s["message_id"] in message_ids, f"Claim source {s['message_id']} not found in session messages"


def test_specific_claim_lookup_endpoint():
    """Verify GET /api/diagnosis/{id}/claims/{claim_id} endpoint."""
    response = client.post("/api/scenarios/01_normal_network.json/run")
    assert response.status_code == 200
    report = response.json()
    session_id = report["extensions"]["session_id"]
    
    claims_resp = client.get(f"/api/diagnosis/{session_id}/claims")
    first_claim_id = claims_resp.json()["claims"][0]["claim_id"]
    
    specific_resp = client.get(f"/api/diagnosis/{session_id}/claims/{first_claim_id}")
    assert specific_resp.status_code == 200
    claim_data = specific_resp.json()
    assert claim_data["claim_id"] == first_claim_id
    assert len(claim_data["sources"]) > 0


def test_ledger_rejects_unsupported_claim():
    """Verify that adding an unsupported claim without sources is flagged with 0 confidence and drops coverage."""
    ledger = ClaimLedger(session_id="TEST-001", incident_id="INC-001")
    
    # 1. Add valid claim
    valid_src = ClaimSource(
        message_id="MSG-1",
        source_agent="performance_agent",
        metric="latency_ms",
        value=150.0,
    )
    c1 = ledger.add_claim("High latency observed", "evidence", [valid_src])
    assert c1.confidence == 1.0
    assert ledger.coverage_pct == 100.0

    # 2. Add unsupported claim
    c2 = ledger.add_claim("Fabricated alien intrusion", "root_cause", [])
    assert c2.confidence == 0.0
    assert len(c2.sources) == 0
    assert ledger.grounded_claims == 1
    assert ledger.total_claims == 2
    assert ledger.coverage_pct == 50.0


def test_markdown_report_includes_footnote_citations():
    """Verify that the markdown report contains footnote tags and citations section."""
    response = client.post("/api/scenarios/07_hackathon_demo.json/run")
    assert response.status_code == 200
    session_id = response.json()["extensions"]["session_id"]
    
    md_resp = client.get(f"/api/diagnosis/{session_id}/report.md")
    assert md_resp.status_code == 200
    content = md_resp.text
    
    assert "[F1]" in content
    assert "Evidence & Claim Traceability Footnotes" in content
    assert "Traceability Provenance Coverage" in content
