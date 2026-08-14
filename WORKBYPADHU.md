# WORK BY PADHU — RailMind Live System Transition & Architecture

## Overview
RailMind is an agentic AI-driven railway traffic management & decision-support platform designed to monitor train telemetry, detect anomalies (delays, signal failures, weather hazards, overcrowding), perform AI reasoning, compute Dijkstra-based detour rerouting, coordinate departmental actions, send SMS alerts, and persist incident logs in real time.

---

## Key Achievements & Implementation Details

### 1. Ingestion & Anomaly Detection Engine (`backend/agents/nodes.py`, `backend/services/railways_api.py`)
- **Telemetry Ingestion**: Integrated live API polling with robust schema validation, null checks, and default fallbacks for missing telemetry fields.
- **Anomaly Detection**: Implemented threshold-based detection rules for:
  - **Delays**: Triggered when delay exceeds 30 minutes.
  - **Signal Failures**: Tracks relay interlock issues and signal grid faults.
  - **Weather Anomalies**: Dense fog visibility reductions (<50m) requiring caution speeds.
  - **Track Blockages / Landslides**: Physical UP/DOWN line obstructions.
  - **Passenger Overcrowding**: Capacity overload (>180%) requiring operational stop buffers.

### 2. Multi-Agent Orchestration & Self-Correction (`backend/agents/graph.py`, `backend/agents/nodes.py`)
- **LangGraph State Graph**: Built a stateful multi-agent loop running through:
  - `ingest_node` -> `detect_node` -> `supervisor_node` -> `reason_node` -> `reroute_node` -> `coordination_node` -> `alert_node` -> `report_node`.
- **Self-Correction & Recovery**:
  - `supervisor_node` evaluates plan validity, detecting maintenance conflicts (e.g. restricted tracks at Kanpur) and clearing bad reasoning state to automatically trigger re-evaluation.
  - Handled tool exceptions gracefully in `reason_with_ai` (`backend/services/ai_service.py`) with high-fidelity dynamic fallbacks for offline or rate-limited environments.

### 3. Complete Indian Railways Graph Topology Reroute (`backend/agents/routing.py`)
- **Graph Expansion**: Built an interconnected graph (`TRACK_GRAPH`) mapping all primary Indian Railways junctions and high-density corridors:
  - **Northern Mainline**: New Delhi (NDLS), Delhi (DLI), Aligarh (ALJN), Kanpur (CNB), Lucknow (LKO), Moradabad (MB), Saharanpur (SRE), Ambala (UMB), Amritsar (ASR), Ludhiana (LDH).
  - **Eastern Corridor**: Prayagraj/Allahabad (ALD), Deen Dayal Upadhyaya/Mughalsarai (MGS), Varanasi (BSB), Patna (PNBE), Dhanbad (DHN), Bardhaman (BWN), Howrah (HWH), Sealdah (SDAH), Kolkata (KOAA).
  - **Central & Western Trunk**: Agra (AGC), Mathura (MTJ), Gwalior (GWL), Jhansi (VGLJ), Bhopal (BPL), Itarsi (ET), Jabalpur (JBP), Nagpur (NGP), Mumbai Central (BCT), Mumbai CST (CSTM), Vadodara (BRC), Surat (ST), Ahmedabad (ADI).
  - **Southern Corridor**: Vijayawada (BZA), Secunderabad (SC), Chennai Central (MAS), Chennai Egmore (MS), Bengaluru (SBC), Pune (PUNE), Solapur (SUR), Hubballi (UBL), Madurai (MDU), Thiruvananthapuram (TVC), Ernakulam (ERS).
- **Dijkstra Detour Algorithm**: Computes shortest travel-time detour paths around blocked or restricted stations.

### 4. Database Persistence & WebSocket Layer (`backend/services/db_client.py`, `backend/api/main.py`)
- **MongoDB Atlas Integration**: Live CRUD operations using Motor async driver with compound index creation (`train_number` + `timestamp`).
- **Graceful Local Fallback**: Maintains `fallback_db.json` with thread/async lock synchronization if database connection is unavailable.
- **WebSocket Broadcasts**: Real-time event broadcasts (`ConnectionManager`) pushing train status updates, anomaly detections, and department tasks to the frontend interface.

### 5. SMS Notification Integration (`backend/services/twilio_service.py`)
- Configured Twilio REST API integration for department dispatch (Maintenance, Operations, Station Manager) and passenger advisories.
- Supports `DEMO_MODE=true` bypass for zero-cost offline demonstrations.

---

## Unit & Integration Test Verification

The system was verified using the project test suite:
- `test_recovery.py`: Verified supervisor conflict routing and tool exception recovery.
- `test_graph.py`: Verified LangGraph multi-node state transitions and streaming.
- `test_all.py`: Verified environment configurations, AI client initialization, MongoDB connection, Railways API ingestion, and WebSocket broadcasting.

---

## How to Run RailMind

### 1. Environment Setup
Create or update `backend/.env`:
```env
MONGODB_URI=mongodb+srv://<user>:<password>@cluster0.mongodb.net/railmind
GEMINI_API_KEY=your_gemini_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_number
DEMO_MODE=true
```

### 2. Launch Backend Application
```powershell
# From project root
uvicorn backend.api.main:app --reload --port 8000
```

### 3. Launch Frontend Application
```powershell
cd frontend
npm run dev
```
Access the application dashboard at `http://localhost:5173`.
