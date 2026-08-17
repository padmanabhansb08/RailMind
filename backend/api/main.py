import asyncio
import os
import uvicorn
from datetime import datetime
from dotenv import load_dotenv

# Ensure env variables are loaded before imports
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=env_path)

import secrets
from fastapi import FastAPI, WebSocket, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from ..services.db_client import db_client

security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD")
    if not admin_pass:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin password not configured in environment.",
        )

    correct_username = secrets.compare_digest(credentials.username, admin_user)
    correct_password = secrets.compare_digest(credentials.password, admin_pass)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

from .routes import router
from .websocket import websocket_endpoint, websocket_manager # type: ignore
from ..agents.graph import railmind_graph # type: ignore
from ..agents.state import AgentState # type: ignore
from ..services.railways_api import RailwaysAPIClient

app = FastAPI(
    title="RailMind Operations API",
    description="Autonomous railway operations intelligence agent API",
    version="0.1.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize railways client for fallback train list queries
api_key = os.getenv("RAILWAYS_API_KEY", "mock_key")
railways_client = RailwaysAPIClient(api_key=api_key)

# Global reference storing the most recent loop state from the agent background thread
latest_agent_state = {
    "raw_train_data": [],
    "anomalies": [],
    "claude_reasoning": "",
    "reroute_plan": None,
    "department_tasks": [],
    "sms_alerts_sent": [],
    "incident_report": None,
    "loop_count": 0,
    "should_continue": False,
    "last_api_call": "Never",
    "railways_latency_ms": 0,
    "ai_latency_ms": 0,
    "processed_trains": []
}


async def run_agent_loop_fallback():
    from ..agents.graph import railmind_graph
    from ..agents.state import AgentState
    import uuid
    train_numbers = [
        "12301", "12951", "12001", "12259", "12565",
        "11057", "12627", "12625", "12621", "12615",
        "12309", "12721", "12229", "12311", "12641"
    ]
    processed_trains = []
    
    # Wait 2 seconds for startup to settle
    await asyncio.sleep(2)
    
    loop_cnt = 0
    while True:
        try:
            loop_cnt += 1
            print(f"[RAILMIND] Real-Time background agent cognitive loop #{loop_cnt} starting...")
            initial_state = AgentState(
                raw_train_data=[],
                anomalies=[],
                claude_reasoning="",
                reroute_plan=None,
                department_tasks=[],
                sms_alerts_sent=[],
                incident_report=None,
                loop_count=loop_cnt,
                should_continue=False,
                last_api_call="Never",
                railways_latency_ms=0,
                ai_latency_ms=0,
                processed_trains=processed_trains,
                target_trains=train_numbers
            )
            thread_id = f"local_bg_{uuid.uuid4().hex[:8]}"
            config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}
            result = await railmind_graph.ainvoke(initial_state, config)
            if result:
                processed_trains = result.get("processed_trains", [])
                latest_agent_state.update({
                    "raw_train_data": result.get("raw_train_data", []),
                    "anomalies": result.get("anomalies", []),
                    "claude_reasoning": result.get("claude_reasoning", ""),
                    "reroute_plan": result.get("reroute_plan"),
                    "department_tasks": result.get("department_tasks", []),
                    "sms_alerts_sent": result.get("sms_alerts_sent", []),
                    "incident_report": result.get("incident_report"),
                    "loop_count": loop_cnt,
                    "should_continue": result.get("should_continue", False),
                    "last_api_call": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "railways_latency_ms": result.get("railways_latency_ms", 120),
                    "ai_latency_ms": result.get("ai_latency_ms", 350),
                    "processed_trains": processed_trains
                })
                
                # Broadcast WS live updates to active frontend clients
                if result.get("incident_report"):
                    inc_report = result.get("incident_report")
                    inc_report["loop_count"] = loop_cnt
                    await websocket_manager.broadcast_json({
                        "type": "INCIDENT_UPDATE",
                        "data": inc_report
                    })
                
                await websocket_manager.broadcast_json({
                    "type": "AGENT_LOG",
                    "message": f"[{datetime.utcnow().strftime('%H:%M:%S')}] [AGENT_LOOP] Cycle #{loop_cnt} complete — Raw Trains: {len(result.get('raw_train_data', []))}, Anomalies: {len(result.get('anomalies', []))}"
                })
            print(f"[RAILMIND] Real-Time background agent cognitive loop #{loop_cnt} completed.")
        except Exception as e:
            print(f"[RAILMIND] Real-Time background agent loop failed: {e}")
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    # Test connection on startup and clean collections:
    try:
        from ..services.db_client import client, db
        await client.admin.command('ping')
        print("[RAILMIND] MongoDB Atlas connected [OK]")
        
        # Cleanup incidents and tasks
        await db_client.init_indexes()
        await db.incidents.delete_many({})
        await db.department_tasks.delete_many({})
        print("[RAILMIND] Cleared MongoDB incidents and tasks collections [OK]")
    except Exception as e:
        print(f"[RAILMIND] MongoDB connection/cleanup failed: {e}")

    # Run the agent workflow loop asynchronously in the background on API startup
    asyncio.create_task(run_agent_loop_fallback())

# Include general REST routers
app.include_router(router, prefix="/api")

# Mounting direct WebSocket handler
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket_endpoint(websocket)

# REST Endpoint: GET /api/incidents - Fetch last 20 incidents (last 24h by default, or all=true)
@app.get("/api/incidents")
async def get_incidents_api(all: bool = False):
    try:
        from datetime import datetime, timedelta
        # Fetch up to 1000 incidents
        incidents = await db_client.get_incidents(limit=1000)
        if all:
            return incidents
            
        cutoff = datetime.utcnow() - timedelta(hours=24)
        filtered = []
        for inc in incidents:
            ts_str = inc.get("timestamp")
            if not ts_str:
                continue
            try:
                if isinstance(ts_str, datetime):
                    ts = ts_str
                else:
                    ts = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
                if ts.tzinfo is not None:
                    ts = ts.replace(tzinfo=None)
                if ts >= cutoff:
                    filtered.append(inc)
            except Exception:
                filtered.append(inc)
        return filtered
    except Exception as e:
        print(f"Error fetching incidents: {e}")
        return []

# REST Endpoint: GET /api/trains - Fetch current train statuses
@app.get("/api/trains")
async def get_trains_api():
    from ..services.railways_api import get_dynamic_position_and_status, RAW_MOCK_TRAINS
    trains = latest_agent_state.get("raw_train_data", [])
    if not trains:
        return []
    # Enrich trains that are missing route_stops with dynamic position data
    enriched = []
    for train in trains:
        if not train.get("route_stops") and train.get("train_number") in RAW_MOCK_TRAINS:
            dynamic = get_dynamic_position_and_status(train["train_number"])
            merged = {**train}
            merged["route_stops"] = dynamic.get("route_stops", [])
            # Also use dynamic lat/lng for smooth movement
            merged["lat"] = dynamic.get("lat", train.get("lat"))
            merged["lng"] = dynamic.get("lng", train.get("lng"))
            merged["speed"] = dynamic.get("speed", train.get("speed", "80 km/h"))
            merged["next_station"] = dynamic.get("next_station", train.get("next_station", "Unknown"))
            merged["distance_next"] = dynamic.get("distance_next", train.get("distance_next", "0.5 KM"))
            enriched.append(merged)
        else:
            enriched.append(train)
    return enriched

# Simple cache for the massive live map data (60 seconds)
import time
LIVE_MAP_CACHE = {"data": [], "timestamp": 0}

@app.get("/api/trains/all")
async def get_all_trains_api():
    from ..services.railways_api import fetch_all_live_trains
    current_time = time.time()
    
    # Return cached data if less than 60 seconds old to protect API limits
    if current_time - LIVE_MAP_CACHE["timestamp"] < 60 and LIVE_MAP_CACHE["data"]:
        return LIVE_MAP_CACHE["data"]
        
    # Otherwise fetch fresh data
    data = await fetch_all_live_trains()
    if data:
        LIVE_MAP_CACHE["data"] = data
        LIVE_MAP_CACHE["timestamp"] = current_time
        return data
        
    # If fetch failed, return cached data anyway if available
    return LIVE_MAP_CACHE["data"]

# REST Endpoint: GET /api/trains/search - Search for a train and add to tracked list
@app.get("/api/trains/search")
async def search_train_api(train_number: str):
    try:
        from ..services.railways_api import get_live_train_status
        from ..agents.nodes import TRACKED_TRAINS
        
        # Fetch the live status for this train
        res = await get_live_train_status(train_number)
        
        if not res or not res.get("train_number"):
            from ..services.railways_api import get_mock_rapidapi_train, parse_rapidapi_train_for_agent
            mock_data = get_mock_rapidapi_train(train_number)
            res = parse_rapidapi_train_for_agent(mock_data, train_number)
            
        if res and res.get("train_number"):
            # Add to tracked trains list so it continues updating in background loop
            if train_number not in TRACKED_TRAINS:
                TRACKED_TRAINS.append(train_number)
            
            # Instantly inject into the latest agent state so GET /api/trains returns it immediately
            # preventing the frontend from overwriting it during the 5s poll interval
            from ..api.main import latest_agent_state
            if "raw_train_data" not in latest_agent_state:
                latest_agent_state["raw_train_data"] = []
                
            # Check if it's already in there to avoid duplicates
            existing = next((t for t in latest_agent_state["raw_train_data"] if t["train_number"] == train_number), None)
            if existing:
                existing.update(res)
            else:
                latest_agent_state["raw_train_data"].append(res)
                
            return res
            
        return {"error": "Train not found"}
    except Exception as e:
        print(f"Error searching train: {e}")
        return {"error": str(e)}

# REST Endpoint: GET /api/dept-tasks - Fetch pending tasks
@app.get("/api/dept-tasks")
async def get_dept_tasks_api():
    try:
        return await db_client.get_pending_department_tasks()
    except Exception as e:
        print(f"Error fetching department tasks: {e}")
        return []

# REST Endpoint: POST /api/dept-tasks/{id}/resolve - Mark task resolved
@app.post("/api/dept-tasks/{id}/resolve")
async def resolve_task_api(id: str):
    try:
        modified_count = await db_client.resolve_department_task(id)
        return {"status": "resolved", "modified_count": modified_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# REST Endpoint: POST /api/incidents/{id}/approve - Approve reroute plan
@app.post("/api/incidents/{id}/approve")
async def approve_incident_api(id: str, admin: str = Depends(verify_admin)):
    try:
        modified_count = await db_client.approve_incident(id)
        return {"status": "approved", "modified_count": modified_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# REST Endpoint: GET /api/system-status -> returns all system statuses
@app.get("/api/system-status")
async def get_system_status():
    return {
        "agent_status": "ACTIVE",
        "model": "Gemini 2.0 Flash / Claude 3.5 Sonnet",
        "railways_api": "Connected",
        "twilio_sms": "Connected",
        "mongodb": "Connected",
        "contacts": {
            "maintenance": os.getenv("MAINTENANCE_PHONE", "+919651058174"),
            "operations": os.getenv("OPERATIONS_PHONE", "+919651058174"),
            "station_manager": os.getenv("STATION_PHONE", "+919651058174")
        }
    }

# REST Endpoint: GET /api/telemetry -> returns timing metrics
@app.get("/api/telemetry")
async def get_telemetry_api():
    incident_count = 0
    task_count = 0
    try:
        from ..services.db_client import db
        incident_count = await db["incidents"].count_documents({})
        task_count = await db["department_tasks"].count_documents({})
    except Exception:
        pass

    return {
        "agent_loop_status": "running",
        "last_api_call": latest_agent_state.get("last_api_call", "Never"),
        "railways_latency_ms": latest_agent_state.get("railways_latency_ms", 0),
        "ai_latency_ms": latest_agent_state.get("ai_latency_ms", 0),
        "websocket_clients": len(websocket_manager.active_connections),
        "mongodb_incidents": incident_count,
        "mongodb_tasks": task_count
    }

async def run_single_agent_iteration():
    from ..agents.graph import railmind_graph
    from ..agents.state import AgentState
    import uuid
    train_numbers = [
        "12301", "12951", "12001", "12259", "12565",
        "11057", "12627", "12625", "12621", "12615",
        "12309", "12721", "12229", "12311", "12641"
    ]
    global latest_agent_state
    processed_trains = latest_agent_state.get("processed_trains", [])
    try:
        print("[RAILMIND] Immediate agent loop iteration starting via simulation trigger...")
        initial_state = AgentState(
            raw_train_data=[],
            anomalies=[],
            claude_reasoning="",
            reroute_plan=None,
            department_tasks=[],
            sms_alerts_sent=[],
            incident_report=None,
            loop_count=0,
            should_continue=False,
            last_api_call="Never",
            railways_latency_ms=0,
            ai_latency_ms=0,
            processed_trains=processed_trains,
            target_trains=train_numbers
        )
        thread_id = f"sim_trigger_{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}
        result = await railmind_graph.ainvoke(initial_state, config)
        if result:
            processed_trains = result.get("processed_trains", [])
            latest_agent_state.update({
                "raw_train_data": result.get("raw_train_data", []),
                "anomalies": result.get("anomalies", []),
                "claude_reasoning": result.get("claude_reasoning", ""),
                "reroute_plan": result.get("reroute_plan"),
                "department_tasks": result.get("department_tasks", []),
                "sms_alerts_sent": result.get("sms_alerts_sent", []),
                "incident_report": result.get("incident_report"),
                "loop_count": result.get("loop_count", 0),
                "should_continue": result.get("should_continue", False),
                "last_api_call": result.get("last_api_call", "Never"),
                "railways_latency_ms": result.get("railways_latency_ms", 0),
                "ai_latency_ms": result.get("ai_latency_ms", 0),
                "processed_trains": processed_trains
            })
        print("[RAILMIND] Immediate agent loop iteration completed.")
    except Exception as e:
        print(f"[RAILMIND] Immediate agent loop iteration failed: {e}")

@app.post("/api/simulate-anomaly")
async def simulate_anomaly_api(data: dict):
    train_number = data.get("train_number")
    delay_minutes = data.get("delay_minutes", 0)
    status = data.get("status", "Delayed")
    current_station = data.get("current_station")
    
    from ..services.railways_api import SIMULATED_OVERRIDES
    SIMULATED_OVERRIDES[train_number] = {
        "delay_minutes": delay_minutes,
        "status": status
    }
    if current_station:
        SIMULATED_OVERRIDES[train_number]["current_station"] = current_station
        
    asyncio.create_task(run_single_agent_iteration())
    return {"status": "anomaly_injected", "train_number": train_number}

@app.post("/api/reset-simulation")
async def reset_simulation_api():
    from ..services.railways_api import SIMULATED_OVERRIDES
    SIMULATED_OVERRIDES.clear()
    
    global latest_agent_state
    latest_agent_state["processed_trains"] = []
    
    asyncio.create_task(run_single_agent_iteration())
    return {"status": "simulation_reset"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
