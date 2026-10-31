import json
import os
import re
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.models.diagnosis import FinalDiagnosisReport

SAFE_SESSION_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


class SessionRecord:
    def __init__(
        self,
        session_id: str,
        incident_id: str,
        created_at: str,
        telemetry_raw: List[Dict[str, Any]],
        topology_raw: Optional[Dict[str, Any]],
        final_report: Optional[FinalDiagnosisReport] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        markdown_report: Optional[str] = None,
    ):
        self.session_id = session_id
        self.incident_id = incident_id
        self.created_at = created_at
        self.telemetry_raw = telemetry_raw
        self.topology_raw = topology_raw
        self.final_report = final_report
        self.messages = messages or []
        self.markdown_report = markdown_report or ""


class SessionStore:
    """Thread-safe file-backed session storage for diagnostic investigations."""

    def __init__(self, storage_dir: str = "data/sessions"):
        self.storage_dir = os.path.abspath(storage_dir)
        os.makedirs(self.storage_dir, exist_ok=True)
        self._memory_store: Dict[str, SessionRecord] = {}
        self._incident_index: Dict[str, str] = {}
        self._counter = 1
        self._lock = threading.Lock()
        self._load_existing_sessions()

    def generate_session_id(self) -> str:
        with self._lock:
            year = datetime.utcnow().year
            sid = f"DX-{year}-{self._counter:04d}"
            self._counter += 1
            return sid

    def save_session(
        self,
        session_id: str,
        incident_id: str,
        telemetry_raw: List[Dict[str, Any]],
        topology_raw: Optional[Dict[str, Any]],
        final_report: Optional[FinalDiagnosisReport],
        messages: List[Dict[str, Any]],
        markdown_report: str,
    ) -> SessionRecord:
        if not session_id or len(session_id) > 64 or not SAFE_SESSION_ID_REGEX.match(session_id):
            raise ValueError(f"Invalid session_id: {session_id}")
        if not incident_id or len(incident_id) > 64 or not SAFE_SESSION_ID_REGEX.match(incident_id):
            raise ValueError(f"Invalid incident_id: {incident_id}")

        now_str = datetime.utcnow().isoformat() + "Z"
        rec = SessionRecord(
            session_id=session_id,
            incident_id=incident_id,
            created_at=now_str,
            telemetry_raw=telemetry_raw,
            topology_raw=topology_raw,
            final_report=final_report,
            messages=messages,
            markdown_report=markdown_report,
        )
        with self._lock:
            self._memory_store[session_id] = rec
            self._incident_index[incident_id] = session_id

        # Atomic Persist to disk inside fixed storage directory
        file_path = os.path.realpath(os.path.join(self.storage_dir, f"{session_id}.json"))
        if not file_path.startswith(self.storage_dir + os.sep):
            raise ValueError(f"Path traversal detected: {file_path}")

        tmp_path = f"{file_path}.tmp"
        try:
            payload = {
                "session_id": session_id,
                "incident_id": incident_id,
                "created_at": now_str,
                "telemetry": telemetry_raw,
                "topology": topology_raw,
                "messages": messages,
                "final_report": final_report.model_dump() if final_report else None,
                "markdown_report": markdown_report,
            }
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.chmod(tmp_path, 0o600)
            os.replace(tmp_path, file_path)
        except Exception:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        return rec

    def get_by_session_id(self, session_id: str) -> Optional[SessionRecord]:
        if not session_id or not SAFE_SESSION_ID_REGEX.match(session_id):
            return None
        return self._memory_store.get(session_id)

    def get_by_incident_id(self, incident_id: str) -> Optional[SessionRecord]:
        if not incident_id or not SAFE_SESSION_ID_REGEX.match(incident_id):
            return None
        sid = self._incident_index.get(incident_id)
        if sid:
            return self._memory_store.get(sid)
        return None

    def list_sessions(self) -> List[Dict[str, Any]]:
        results = []
        for sid, rec in self._memory_store.items():
            results.append(
                {
                    "session_id": rec.session_id,
                    "incident_id": rec.incident_id,
                    "created_at": rec.created_at,
                    "status": rec.final_report.status.value if rec.final_report else "pending",
                    "root_cause": rec.final_report.suspected_root_cause if rec.final_report else "Analyzing...",
                    "confidence": rec.final_report.confidence if rec.final_report else 0.0,
                    "affected_devices_count": len(rec.final_report.affected_devices) if rec.final_report else 0,
                    "message_count": len(rec.messages),
                }
            )
        return sorted(results, key=lambda x: x["created_at"], reverse=True)

    def get_latest(self) -> Optional[SessionRecord]:
        with self._lock:
            if not self._memory_store:
                return None
            sorted_records = sorted(self._memory_store.values(), key=lambda r: r.created_at, reverse=True)
            return sorted_records[0]

    def _load_existing_sessions(self) -> None:
        if not os.path.exists(self.storage_dir):
            return
        for fname in os.listdir(self.storage_dir):
            if fname.endswith(".json"):
                try:
                    fpath = os.path.join(self.storage_dir, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    sid = data.get("session_id")
                    inc = data.get("incident_id")
                    if sid and inc:
                        report_data = data.get("final_report")
                        report_obj = FinalDiagnosisReport(**report_data) if report_data else None
                        rec = SessionRecord(
                            session_id=sid,
                            incident_id=inc,
                            created_at=data.get("created_at", ""),
                            telemetry_raw=data.get("telemetry", []),
                            topology_raw=data.get("topology"),
                            final_report=report_obj,
                            messages=data.get("messages", []),
                            markdown_report=data.get("markdown_report", ""),
                        )
                        self._memory_store[sid] = rec
                        self._incident_index[inc] = sid
                except Exception:
                    continue


# Global singleton instance
session_store = SessionStore()
