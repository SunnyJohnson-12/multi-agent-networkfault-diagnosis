import os
import re
import json
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.orchestration.orchestrator import orchestrator
from app.services.session_store import session_store
from app.validation.validators import ValidationErrorResponse, validate_telemetry_item, validate_topology
from app.models.diagnosis import FinalDiagnosisReport

api_router = APIRouter()

SAFE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")
SAFE_SCENARIO_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
MAX_TELEMETRY_ITEMS = 500

SCENARIOS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/scenarios"))
TOPOLOGY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/topology/campus_topology.json"))


def load_default_topology() -> Dict[str, Any]:
    if os.path.exists(TOPOLOGY_FILE):
        with open(TOPOLOGY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"nodes": [], "links": []}


def validate_identifier(identifier: str, param_name: str = "identifier") -> str:
    if not identifier or len(identifier) > 64 or not SAFE_ID_REGEX.match(identifier):
        raise HTTPException(status_code=400, detail=f"Invalid {param_name} format")
    return identifier


class DiagnoseRequest(BaseModel):
    telemetry: List[Dict[str, Any]] = Field(..., max_length=MAX_TELEMETRY_ITEMS, description="Array of raw device telemetry objects")
    topology: Optional[Dict[str, Any]] = Field(None, description="Campus topology JSON (optional)")
    incident_id: Optional[str] = Field(None, max_length=64, description="Optional caller incident identifier")
    disabled_agents: Optional[List[str]] = Field(default_factory=list, max_length=10, description="Agents to disable for 'What-if' tests")


class ScenarioRunRequest(BaseModel):
    disabled_agents: Optional[List[str]] = Field(default_factory=list, max_length=10, description="List of agents to disable")


@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Multi-Agent Network Fault Diagnosis System",
        "version": "1.0.0",
        "active_agents": [
            "performance_agent",
            "infrastructure_agent",
            "connectivity_agent",
            "correlation_agent",
            "reporting_agent",
        ],
    }


@api_router.get("/topology")
async def get_topology():
    return load_default_topology()


@api_router.post("/telemetry")
async def store_and_validate_telemetry(payload: Dict[str, Any]):
    records = payload.get("records")
    if records is None:
        records = [payload]
    elif not isinstance(records, list):
        raise HTTPException(status_code=400, detail="'records' must be a list of telemetry objects")
    
    if len(records) > MAX_TELEMETRY_ITEMS:
        raise HTTPException(status_code=400, detail=f"Too many telemetry records. Maximum is {MAX_TELEMETRY_ITEMS}")

    validated = []
    for r in records:
        try:
            val = validate_telemetry_item(r)
            validated.append(val.model_dump())
        except ValidationErrorResponse as e:
            return Response(
                content=json.dumps(e.to_dict()),
                status_code=400,
                media_type="application/json",
            )
    return {"validated": True, "count": len(validated), "records": validated}


@api_router.post("/diagnose")
async def run_diagnose(request: DiagnoseRequest):
    if request.incident_id:
        validate_identifier(request.incident_id, "incident_id")
    topology_data = request.topology or load_default_topology()
    try:
        session_rec = await orchestrator.run_diagnostic_session(
            telemetry_raw=request.telemetry,
            topology_raw=topology_data,
            incident_id=request.incident_id,
            disabled_agents=request.disabled_agents,
        )
        if not session_rec.final_report:
            raise HTTPException(status_code=500, detail="Failed to generate diagnostic report")
        return session_rec.final_report.to_section6_dict(include_extensions=True)
    except ValidationErrorResponse as e:
        return Response(
            content=json.dumps(e.to_dict()),
            status_code=400,
            media_type="application/json",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/diagnosis/{session_or_incident_id}")
async def get_diagnosis(session_or_incident_id: str):
    valid_id = validate_identifier(session_or_incident_id, "session_or_incident_id")
    rec = session_store.get_by_session_id(valid_id) or session_store.get_by_incident_id(valid_id)
    if not rec or not rec.final_report:
        raise HTTPException(status_code=404, detail="Diagnosis record not found")
    return rec.final_report.to_section6_dict(include_extensions=True)


@api_router.get("/messages")
async def get_messages(session_id: Optional[str] = None):
    rec = None
    if session_id:
        valid_id = validate_identifier(session_id, "session_id")
        rec = session_store.get_by_session_id(valid_id) or session_store.get_by_incident_id(valid_id)
    else:
        rec = session_store.get_latest()
    if not rec:
        return {"session_id": None, "messages": []}
    return {"session_id": rec.session_id, "messages": rec.messages}


@api_router.get("/findings")
async def get_findings(session_id: Optional[str] = None):
    rec = None
    if session_id:
        valid_id = validate_identifier(session_id, "session_id")
        rec = session_store.get_by_session_id(valid_id) or session_store.get_by_incident_id(valid_id)
    else:
        rec = session_store.get_latest()
    if not rec:
        return {"session_id": None, "findings": []}
    findings = [
        m
        for m in rec.messages
        if m.get("message_type") in ("diagnostic_finding", "clarification_response", "consolidated_diagnosis")
    ]
    return {"session_id": rec.session_id, "findings": findings}


@api_router.get("/diagnosis/{session_or_incident_id}/messages")
async def get_diagnosis_messages(session_or_incident_id: str):
    valid_id = validate_identifier(session_or_incident_id, "session_or_incident_id")
    rec = session_store.get_by_session_id(valid_id) or session_store.get_by_incident_id(valid_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": rec.session_id, "messages": rec.messages}


@api_router.get("/diagnosis/{session_or_incident_id}/findings")
async def get_diagnosis_findings(session_or_incident_id: str):
    valid_id = validate_identifier(session_or_incident_id, "session_or_incident_id")
    rec = session_store.get_by_session_id(valid_id) or session_store.get_by_incident_id(valid_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Session not found")
    findings = [
        m
        for m in rec.messages
        if m.get("message_type") in ("diagnostic_finding", "clarification_response", "consolidated_diagnosis")
    ]
    return {"session_id": rec.session_id, "findings": findings}


@api_router.get("/diagnosis/{session_or_incident_id}/report.md")
async def get_diagnosis_markdown(session_or_incident_id: str):
    valid_id = validate_identifier(session_or_incident_id, "session_or_incident_id")
    rec = session_store.get_by_session_id(valid_id) or session_store.get_by_incident_id(valid_id)
    if not rec or not rec.markdown_report:
        raise HTTPException(status_code=404, detail="Markdown report not found")
    return Response(content=rec.markdown_report, media_type="text/markdown")


@api_router.get("/diagnosis/{session_or_incident_id}/claims")
async def get_diagnosis_claims(session_or_incident_id: str):
    valid_id = validate_identifier(session_or_incident_id, "session_or_incident_id")
    rec = session_store.get_by_session_id(valid_id) or session_store.get_by_incident_id(valid_id)
    if not rec or not rec.final_report:
        raise HTTPException(status_code=404, detail="Session not found")
    ext = rec.final_report.extensions
    claims = ext.claim_ledger if ext else []
    traceability = ext.traceability if ext else {}
    return {
        "session_id": rec.session_id,
        "incident_id": rec.incident_id,
        "traceability": traceability,
        "claims": claims,
    }


@api_router.get("/diagnosis/{session_or_incident_id}/claims/{claim_id}")
async def get_specific_claim(session_or_incident_id: str, claim_id: str):
    valid_id = validate_identifier(session_or_incident_id, "session_or_incident_id")
    valid_cid = validate_identifier(claim_id, "claim_id")
    rec = session_store.get_by_session_id(valid_id) or session_store.get_by_incident_id(valid_id)
    if not rec or not rec.final_report:
        raise HTTPException(status_code=404, detail="Session not found")
    ext = rec.final_report.extensions
    claims = ext.claim_ledger if ext else []
    for c in claims:
        if c.get("claim_id") == valid_cid:
            return c
    raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found")


@api_router.post("/diagnosis/{session_or_incident_id}/ablation")
@api_router.get("/diagnosis/{session_or_incident_id}/ablation")
async def get_or_run_ablation(session_or_incident_id: str):
    from app.services.ablation import run_ablation
    valid_id = validate_identifier(session_or_incident_id, "session_or_incident_id")
    rec = session_store.get_by_session_id(valid_id) or session_store.get_by_incident_id(valid_id)
    if not rec or not rec.final_report:
        raise HTTPException(status_code=404, detail="Diagnosis record not found")

    ext = rec.final_report.extensions
    if ext and ext.ablation:
        return ext.ablation

    try:
        report = await run_ablation(
            telemetry=rec.telemetry_raw,
            topology=rec.topology_raw,
            baseline_report=rec.final_report,
            session_id=rec.session_id,
            incident_id=rec.incident_id,
        )
        report_dict = report.model_dump()
        if ext:
            ext.ablation = report_dict
        # Persist updated session
        session_store.save_session(
            session_id=rec.session_id,
            incident_id=rec.incident_id,
            telemetry_raw=rec.telemetry_raw,
            topology_raw=rec.topology_raw,
            final_report=rec.final_report,
            messages=rec.messages,
            markdown_report=rec.markdown_report,
        )
        return report_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run ablation: {str(e)}")


@api_router.get("/scenarios")
async def list_scenarios():
    scenarios = []
    if os.path.exists(SCENARIOS_DIR):
        for fname in sorted(os.listdir(SCENARIOS_DIR)):
            if fname.endswith(".json"):
                fpath = os.path.join(SCENARIOS_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    scenarios.append(
                        {
                            "file": fname,
                            "scenario_id": data.get("scenario_id", fname),
                            "name": data.get("name", fname),
                            "description": data.get("description", ""),
                            "expected_fault": data.get("expected_fault", ""),
                            "incident_id": data.get("incident_id", ""),
                            "disabled_agents": data.get("disabled_agents", []),
                            "telemetry_count": len(data.get("telemetry", [])),
                        }
                    )
                except Exception:
                    continue
    return scenarios


@api_router.post("/scenarios/{name}/run")
async def run_scenario(name: str, req: Optional[ScenarioRunRequest] = None):
    # Strict validation of scenario name
    if not name or len(name) > 64 or ".." in name or "/" in name or "\\" in name or "\x00" in name or not SAFE_SCENARIO_REGEX.match(name):
        raise HTTPException(status_code=400, detail="Invalid scenario name")

    target_file = None
    if os.path.exists(SCENARIOS_DIR):
        real_scenarios_dir = os.path.realpath(SCENARIOS_DIR)
        for fname in sorted(os.listdir(SCENARIOS_DIR)):
            if not fname.endswith(".json"):
                continue
            if fname == name or fname == f"{name}.json" or fname.startswith(f"{name}_"):
                cand = os.path.realpath(os.path.join(SCENARIOS_DIR, fname))
                if cand.startswith(real_scenarios_dir + os.sep) and os.path.exists(cand):
                    target_file = cand
                    break

    if not target_file or not os.path.exists(target_file):
        raise HTTPException(status_code=404, detail=f"Scenario '{name}' not found")

    with open(target_file, "r", encoding="utf-8") as f:
        scenario_data = json.load(f)

    telemetry = scenario_data.get("telemetry", [])
    topology = load_default_topology()
    incident_id = scenario_data.get("incident_id")
    disabled = (req.disabled_agents if req and req.disabled_agents else None) or scenario_data.get(
        "disabled_agents", []
    )

    try:
        session_rec = await orchestrator.run_diagnostic_session(
            telemetry_raw=telemetry,
            topology_raw=topology,
            incident_id=incident_id,
            disabled_agents=disabled,
        )
        if not session_rec.final_report:
            raise HTTPException(status_code=500, detail="Failed to generate diagnostic report")
        return session_rec.final_report.to_section6_dict(include_extensions=True)
    except ValidationErrorResponse as e:
        return Response(
            content=json.dumps(e.to_dict()),
            status_code=400,
            media_type="application/json",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- FEATURE 2: FAULT INJECTION STUDIO ROUTES ---

class InjectionRequest(BaseModel):
    base_scenario: Optional[str] = Field("01_normal_network.json", max_length=64)
    injections: Optional[List[Dict[str, Any]]] = Field(default_factory=list, max_length=50)
    preset: Optional[str] = Field(None, max_length=32)
    seed: Optional[int] = Field(None, ge=0, le=2147483647)
    couple_metrics: Optional[bool] = True
    disabled_agents: Optional[List[str]] = Field(default_factory=list, max_length=10)


@api_router.get("/inject/presets")
async def get_fault_presets():
    from app.services.fault_injector import PRESETS
    return {
        "presets": [
            {
                "name": p.name,
                "description": p.description,
                "target_device": p.target_device,
                "injections": p.injections,
            }
            for p in PRESETS.values()
        ]
    }


def _load_base_scenario(name: str) -> Dict[str, Any]:
    safe_name = name if name.endswith(".json") else f"{name}.json"
    fpath = os.path.realpath(os.path.join(SCENARIOS_DIR, safe_name))
    if not fpath.startswith(os.path.realpath(SCENARIOS_DIR) + os.sep) or not os.path.exists(fpath):
        # Fallback to 01_normal_network.json
        fpath = os.path.join(SCENARIOS_DIR, "01_normal_network.json")
    with open(fpath, "r", encoding="utf-8") as f:
        return json.load(f)


@api_router.post("/inject")
async def inject_faults(req: InjectionRequest):
    from app.services.fault_injector import FaultInjector
    scenario_data = _load_base_scenario(req.base_scenario or "01_normal_network.json")
    base_telemetry = scenario_data.get("telemetry", [])
    topology = load_default_topology()

    try:
        injected = FaultInjector.inject(
            base_telemetry=base_telemetry,
            topology=topology,
            injections=req.injections,
            preset=req.preset,
            couple_metrics=req.couple_metrics if req.couple_metrics is not None else True,
            seed=req.seed,
        )
        return {
            "telemetry": injected,
            "topology": topology,
            "preset": req.preset,
            "seed": req.seed,
            "simulated": True,
            "badge": "SIMULATED TELEMETRY",
        }
    except ValidationErrorResponse as e:
        return Response(content=json.dumps(e.to_dict()), status_code=400, media_type="application/json")


@api_router.post("/inject/diagnose")
async def inject_and_diagnose(req: InjectionRequest):
    import uuid
    from app.services.fault_injector import FaultInjector
    scenario_data = _load_base_scenario(req.base_scenario or "01_normal_network.json")
    base_telemetry = scenario_data.get("telemetry", [])
    topology = load_default_topology()

    try:
        injected = FaultInjector.inject(
            base_telemetry=base_telemetry,
            topology=topology,
            injections=req.injections,
            preset=req.preset,
            couple_metrics=req.couple_metrics if req.couple_metrics is not None else True,
            seed=req.seed,
        )
        incident_id = f"INC-CHAOS-{uuid.uuid4().hex[:4].upper()}"
        session_rec = await orchestrator.run_diagnostic_session(
            telemetry_raw=injected,
            topology_raw=topology,
            incident_id=incident_id,
            disabled_agents=req.disabled_agents,
        )
        if not session_rec.final_report:
            raise HTTPException(status_code=500, detail="Failed to generate diagnostic report")
        
        result = session_rec.final_report.to_section6_dict(include_extensions=True)
        if "extensions" in result:
            result["extensions"]["simulated_telemetry"] = True
            result["extensions"]["fault_injection"] = {
                "preset": req.preset,
                "seed": req.seed,
                "injection_count": len(req.injections or []),
                "badge": "SIMULATED TELEMETRY",
            }
        return result
    except ValidationErrorResponse as e:
        return Response(content=json.dumps(e.to_dict()), status_code=400, media_type="application/json")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- FEATURE 3: CALIBRATION ROUTES ---

@api_router.get("/calibration")
async def get_calibration():
    from app.services.calibration import CalibrationEngine
    rep = CalibrationEngine.get_latest_report()
    if not rep:
        # Run a baseline calibration with 60 samples if none exists
        report_obj = await CalibrationEngine.run_calibration(num_runs=60, seed=42)
        return report_obj.model_dump()
    return rep


@api_router.post("/calibration/run")
async def run_calibration_endpoint(runs: int = 60, seed: int = 42):
    from app.services.calibration import CalibrationEngine
    if runs < 6 or runs > 300:
        raise HTTPException(status_code=400, detail="'runs' must be between 6 and 300")
    report_obj = await CalibrationEngine.run_calibration(num_runs=runs, seed=seed)
    return report_obj.model_dump()
