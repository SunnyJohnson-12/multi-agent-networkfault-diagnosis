# Interactive Demo & Reproduction Guide

## 1. Quick Start (Zero External Dependencies)

The standalone CLI demo runs immediately on macOS/Linux using Python with zero external API keys or network dependencies required.

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Run the flagship hackathon scenario (12-device shared uplink congestion)
python demo.py --scenario 07_hackathon_demo.json

# 3. List all 8 available scenarios
python demo.py --list

# 4. Run multi-agent degradation proof ("What if an agent were missing?")
python demo.py --scenario 07_hackathon_demo.json --disable-agent infrastructure_agent
```

---

## 2. Launching Full Stack (FastAPI + React Dashboard)

### Backend:
```bash
source .venv/bin/activate
uvicorn app.main:app --app-dir backend --port 8000 --reload
```

### Frontend:
```bash
cd frontend
npm run dev
```

Visit: `http://localhost:5173`

---

## 3. Demo Walkthrough Sequence (2 Minutes)

1. **At-A-Glance Status Bar**: Point out incident `INC-8832`, `CRITICAL` severity chip, `96%` link congestion verdict, and `88%` confidence gauge.
2. **Live Topology Heatmap**: Show the campus network layout. Point to `HOSTEL_CORE_SW_01` pulsing with the red **blast-radius sonar ripple**, while the link to the core router flashes dashed red.
3. **Agent Conversation Stream ("Agent Wire")**:
   - Step through the dispatch from Orchestrator.
   - Show findings from Performance (saturation), Infrastructure (14,230 queue drops), and Connectivity (12 nodes).
   - Click the gold **CROSS-QUERY** badge to inspect the real JSON request/response dialogue between Correlation and Connectivity agents.
4. **Hypothesis Race**: Show how Bandwidth Congestion leads at `0.88`, followed by Buffer Exhaustion at `0.58`.
5. **The Killer "What If An Agent Were Missing?" Toggle**:
   - Click the toggle switch next to **Infrastructure Agent** to turn it off.
   - Notice the instant re-diagnosis: confidence drops to `62%`, and a yellow warning limitation appears: *"Agent failure/timeout: 'infrastructure_agent' was unavailable"*.
   - Re-enable it to demonstrate confidence restoring to `88%`.
6. **Strict Section 6 Report**: Switch to the "Section 6 Report" tab to show schema compliance and human-review action wording.
