import asyncio
import os
import uvicorn
from datetime import datetime, timezone
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
from ..services.triage import parse_time as triage_parse_time

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
    "processed_trains": [],
    # Heartbeat fields — the health probes read these to decide whether the
    # orchestrator is actually alive rather than assuming it is.
    "last_loop_at": None,
    "last_loop_error": None
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
                    "processed_trains": processed_trains,
                    "last_loop_at": datetime.now(timezone.utc).isoformat(),
                    "last_loop_error": None
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
            # Record the failure so /api/system-status can report a degraded
            # loop instead of claiming everything is running.
            latest_agent_state["last_loop_error"] = f"{type(e).__name__}: {e}"
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    # Verify the database connection and ensure indexes exist.
    #
    # Incident and task history is deliberately preserved across restarts:
    # analytics (resolution times, recurrence, trends) are only meaningful if
    # the record survives a reboot. Use RAILMIND_RESET_ON_START=true for a
    # clean slate before a demo.
    from ..services.db_client import client, db
    if client is None:
        print("[RAILMIND] MONGODB_URI not set — using local JSON fallback store")
    else:
        try:
            await client.admin.command('ping')
            print("[RAILMIND] MongoDB Atlas connected [OK]")
            await db_client.init_indexes()

            if os.getenv("RAILMIND_RESET_ON_START") == "true":
                await db.incidents.delete_many({})
                await db.department_tasks.delete_many({})
                print("[RAILMIND] RAILMIND_RESET_ON_START=true — cleared incidents and tasks")
        except Exception as e:
            print(f"[RAILMIND] MongoDB connection failed: {e}")

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

    # Fill gaps only. This previously overwrote live coordinates with simulated
    # ones "for smooth movement", which plotted a real tracked train hundreds of
    # kilometres from where it actually was — and stamped a literal "80 km/h" on
    # top. A simulated position is a legitimate fallback when there is no live
    # fix; it is never an improvement on one, so `position_source` records which
    # the client is looking at.
    enriched = []
    for train in trains:
        merged = {**train}
        # Trust the tag the fetch layer stamped — it knows which upstream
        # actually served the record. Only fall back to inference when the
        # record predates tagging; the presence of coordinates says nothing
        # about whether they are real.
        has_coords = train.get("lat") is not None and train.get("lng") is not None
        if not merged.get("position_source"):
            merged["position_source"] = "unknown"
        has_live_fix = merged["position_source"] == "live" and has_coords

        # A RailRadar record already carries a real route and position; there
        # is nothing here worth "enriching" and everything to lose by mixing
        # simulated values into it.
        if merged.get("data_source") == "railradar":
            enriched.append(merged)
            continue

        if train.get("train_number") in RAW_MOCK_TRAINS:
            dynamic = get_dynamic_position_and_status(train["train_number"])

            # Only a simulated train gets the simulated route. Filling it onto
            # a live train drew an invented corridor under a real position —
            # for 12951 that meant a 705 km straight line from Mathura to
            # Vadodara that matches no actual track. A live train carries the
            # one segment the feed genuinely knows (current -> next stop).
            if not merged.get("route_stops") and not has_live_fix:
                merged["route_stops"] = dynamic.get("route_stops", [])

            if not has_live_fix:
                merged["lat"] = dynamic.get("lat")
                merged["lng"] = dynamic.get("lng")
                merged["position_source"] = "simulated"

            # Leave these absent rather than substituting a plausible number.
            for field in ("speed", "next_station", "distance_next"):
                if merged.get(field) in (None, "", "Unknown") and dynamic.get(field) is not None:
                    merged[field] = dynamic.get(field)
                    merged.setdefault("simulated_fields", []).append(field)

        enriched.append(merged)
    return enriched

# Simple cache for the massive live map data (60 seconds)
import time
LIVE_MAP_CACHE = {"data": [], "timestamp": 0}

async def get_live_network(max_age_seconds: int = 60):
    """Live network snapshot, shared by the map and the impact forecast.

    Both features need the same ~2,700-train payload, so they share one cache
    entry and one upstream call rather than doubling the request rate.
    """
    from ..services.railways_api import fetch_all_live_trains
    current_time = time.time()

    if current_time - LIVE_MAP_CACHE["timestamp"] < max_age_seconds and LIVE_MAP_CACHE["data"]:
        return LIVE_MAP_CACHE["data"]

    data = await fetch_all_live_trains()
    if data:
        LIVE_MAP_CACHE["data"] = data
        LIVE_MAP_CACHE["timestamp"] = current_time
        return data

    # Upstream failed — stale data beats no data, but never invent any.
    return LIVE_MAP_CACHE["data"]


@app.get("/api/trains/all")
async def get_all_trains_api():
    return await get_live_network()

# REST Endpoint: GET /api/trains/{id}/detail - Full route + real-time status
#
# The authoritative view of a single train: complete route geometry joined with
# per-stop running status, the current position, delay, and any exceptions.
@app.get("/api/trains/{train_number}/detail")
async def get_train_detail_api(train_number: str, journey_date: str = None):
    from ..services.railradar import get_train, TrainNotFound, RailRadarUnavailable

    query = (train_number or "").strip()
    if not (query.isdigit() and len(query) == 5):
        raise HTTPException(status_code=400, detail="Enter a 5-digit train number, for example 19310.")

    try:
        return await get_train(query, journey_date)
    except TrainNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RailRadarUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Live tracking unavailable: {e}")


def railradar_to_train_record(detail):
    """Adapt a RailRadar detail payload to the shape the map/list expect."""
    position = detail.get("position") or {}
    next_halt = detail.get("next_halt") or {}
    route = [
        {"code": s["code"], "name": s["name"], "lat": s["lat"], "lng": s["lng"],
         "status": s.get("status"), "sequence": s.get("sequence")}
        for s in detail.get("route", [])
        if s.get("lat") is not None and s.get("lng") is not None
    ]

    # Describe position from RailRadar's own reading: it says whether the train
    # is standing at a stop or running between halts, so neither has to be
    # inferred from coordinates.
    prev_name = (detail.get("previous_halt") or {}).get("stationName")
    next_name = (next_halt or {}).get("stationName")
    if position.get("status") == "at-station" and position.get("station_name"):
        position_label = f"At {position['station_name']}"
    elif prev_name and next_name:
        position_label = f"Between {prev_name} and {next_name}"
    elif position.get("station_name"):
        position_label = f"Near {position['station_name']}"
    else:
        position_label = None

    if position.get("is_actual_position") is False and position_label:
        position_label += " (position inferred from timetable, not observed)"

    delay = detail.get("delay_minutes")
    status = "on_time"
    if detail.get("run_status") == "cancelled":
        status = "cancelled"
    elif isinstance(delay, (int, float)) and delay > 15:
        status = "delayed"

    return {
        "train_number": detail["train_number"],
        "train_name": detail.get("train_name"),
        "source": (detail.get("source") or {}).get("name"),
        "destination": (detail.get("destination") or {}).get("name"),
        "delay_minutes": delay if isinstance(delay, (int, float)) else 0,
        "status": status,
        "current_station": position.get("station_name"),
        "station_code": position.get("station_code"),
        "lat": position.get("lat"),
        "lng": position.get("lng"),
        "next_station": next_halt.get("stationName"),
        "position_label": position_label,
        "route_stops": route,
        # Full timetable route, so nothing downstream needs to invent one.
        "route_is_partial": False,
        "position_source": "live" if detail.get("is_live") else "unknown",
        "is_live": detail.get("is_live"),
        "tracking_mode": detail.get("tracking_mode"),
        "last_updated_at": detail.get("last_updated_at"),
        "is_actual_position": position.get("is_actual_position"),
        "exceptions": detail.get("exceptions") or [],
        # Marks the record as fully sourced, so /api/trains leaves it alone
        # rather than blending simulated route or position data into it.
        "data_source": "railradar",
    }


# REST Endpoint: GET /api/trains/search - Search for a train and add to tracked list
@app.get("/api/trains/search")
async def search_train_api(train_number: str):
    from ..services.railways_api import get_live_train_status
    from ..agents.nodes import TRACKED_TRAINS

    # Indian Railways numbers are five digits. Rejecting anything else up front
    # keeps junk out of TRACKED_TRAINS, which the background loop then polls.
    query = (train_number or "").strip()
    if not (query.isdigit() and len(query) == 5):
        raise HTTPException(
            status_code=400,
            detail="Enter a 5-digit train number, for example 12301.",
        )

    from ..services.railradar import get_train, TrainNotFound, RailRadarUnavailable

    try:
        # RailRadar first: it is the only source that returns the full route
        # with coordinates plus a real-time position, so a hit here gives the
        # map genuine geometry instead of a two-point stub.
        res = None
        try:
            res = railradar_to_train_record(await get_train(query))
        except TrainNotFound:
            raise HTTPException(status_code=404, detail=f"No train {query} found.")
        except RailRadarUnavailable as e:
            print(f"[RAILMIND] RailRadar unavailable for {query}, falling back: {e}")
            res = await get_live_train_status(query)

        # No synthesised stand-in here: if no source knows this train, say so.
        if not res or not res.get("train_number"):
            raise HTTPException(
                status_code=404,
                detail=f"No train {query} found in the live network feed.",
            )

        train_number = query
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

        raise HTTPException(status_code=404, detail=f"No train {query} found.")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error searching train {query}: {e}")
        raise HTTPException(status_code=502, detail=f"Train lookup failed: {e}")

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

# REST Endpoint: GET /api/decision-queue - Deduplicated, ranked operator queue
@app.get("/api/decision-queue")
async def get_decision_queue_api(include_resolved: bool = False):
    from ..services.triage import build_queue, apply_network_impact
    incidents = await db_client.get_incidents(limit=1000)
    cards = build_queue(incidents, include_resolved=include_resolved)

    # Network impact is best-effort: if the live feed is down the queue still
    # ranks on incident data alone rather than failing outright.
    try:
        cards = apply_network_impact(cards, await get_live_network())
    except Exception as e:
        print(f"[RAILMIND] Network impact enrichment skipped: {e}")
    return cards


# REST Endpoint: GET /api/incidents/{id}/impact - Trains converging on a station
@app.get("/api/incidents/{id}/impact")
async def get_incident_impact_api(id: str, window_minutes: int = 30):
    from ..services.triage import build_queue
    from ..services.impact import forecast

    cards = build_queue(await db_client.get_incidents(limit=1000), include_resolved=True)
    card = next((c for c in cards if c["id"] == id or id in (c["duplicate_ids"] or [])), None)
    if not card:
        raise HTTPException(status_code=404, detail=f"No incident matching {id}")

    return forecast(
        card.get("station"),
        await get_live_network(),
        window_minutes=window_minutes,
        exclude_train=card.get("train_number"),
    )

# REST Endpoint: POST /api/incidents/{id}/decision - Record an operator decision
#
# Approving or modifying a plan commits the system to dispatching work, so both
# require admin credentials. Acknowledge, reject and undo do not dispatch
# anything and stay available to any operator at the console.
@app.post("/api/incidents/{id}/decision")
async def record_decision_api(id: str, payload: dict):
    action = (payload or {}).get("action")
    if action not in {"approve", "modify", "reject", "acknowledge", "undo"}:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    actor = "operator"
    if action in {"approve", "modify"}:
        admin_pass = os.getenv("ADMIN_PASSWORD")
        if not admin_pass:
            raise HTTPException(
                status_code=503,
                detail="ADMIN_PASSWORD is not configured, so plans cannot be approved on this deployment.",
            )
        if not secrets.compare_digest(str((payload or {}).get("password") or ""), admin_pass):
            raise HTTPException(status_code=401, detail="Incorrect admin password")
        actor = os.getenv("ADMIN_USERNAME", "admin")

    if action == "modify" and not (payload or {}).get("plan"):
        raise HTTPException(status_code=400, detail="A replacement plan is required to modify.")

    # A queue card can represent several recurrences of the same situation.
    # The operator decided about the situation, not about one row, so the
    # decision applies to every incident behind the card — otherwise the card
    # reappears immediately, still showing its duplicates as unresolved.
    from ..services.triage import build_queue
    targets = [id]
    try:
        cards = build_queue(await db_client.get_incidents(limit=1000), include_resolved=True)
        card = next((c for c in cards if c["id"] == id or id in (c["duplicate_ids"] or [])), None)
        if card:
            targets = [card["id"]] + [d for d in (card["duplicate_ids"] or []) if d]
    except Exception as e:
        print(f"[RAILMIND] Could not expand decision group for {id}: {e}")

    try:
        modified = 0
        for target in targets:
            modified += await db_client.record_decision(
                target,
                action=action,
                actor=actor,
                reason=(payload or {}).get("reason"),
                plan=(payload or {}).get("plan"),
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if modified == 0:
        raise HTTPException(status_code=404, detail=f"No incident matching {id}")

    await websocket_manager.broadcast_json({
        "type": "DECISION_RECORDED",
        "data": {"incident_id": id, "action": action, "actor": actor, "affected": len(targets)}
    })
    return {"status": action, "modified_count": modified, "incidents_affected": len(targets)}

# REST Endpoint: POST /api/incidents/{id}/acknowledge - Persist a dismissal
@app.post("/api/incidents/{id}/acknowledge")
async def acknowledge_incident_api(id: str):
    try:
        modified_count = await db_client.acknowledge_incident(id)
        if modified_count == 0:
            raise HTTPException(status_code=404, detail=f"No incident matching {id}")
        return {"status": "acknowledged", "modified_count": modified_count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# REST Endpoint: GET /api/analytics -> figures computed from stored incidents
@app.get("/api/analytics")
async def get_analytics_api():
    return await db_client.get_analytics()

# REST Endpoint: GET /api/system-status -> live probe of every subsystem
@app.get("/api/system-status")
async def get_system_status():
    from ..services.health import collect_system_status
    return await collect_system_status(latest_agent_state)

# REST Endpoint: GET /api/telemetry -> returns timing metrics
@app.get("/api/telemetry")
async def get_telemetry_api():
    from ..services.health import check_agent_loop

    # get_counts() times out fast and falls back to the JSON store, so a dead
    # database degrades this endpoint instead of hanging it.
    incident_count, task_count = await db_client.get_counts()
    loop = check_agent_loop(latest_agent_state)

    return {
        "agent_loop_status": loop["status"],
        "agent_loop_detail": loop["detail"],
        "last_api_call": latest_agent_state.get("last_api_call", "Never"),
        "railways_latency_ms": latest_agent_state.get("railways_latency_ms", 0),
        "ai_latency_ms": latest_agent_state.get("ai_latency_ms", 0),
        "websocket_clients": len(websocket_manager.active_connections),
        "store": "fallback_file" if db_client.use_fallback else "mongodb",
        "incident_count": incident_count,
        "task_count": task_count
    }

async def run_single_agent_iteration(focus_train: str = None):
    """Run one cognitive cycle immediately.

    `focus_train` is the train an operator just injected from the simulation
    portal. It is pushed to the front of the polled set and cleared from
    `processed_trains`, because detect_node skips any train it has already
    reported on — without that reset an injected delay would be silently
    dropped and never appear in Incident Alerts.
    """
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
    if focus_train:
        focus_train = str(focus_train)
        train_numbers = [focus_train] + [t for t in train_numbers if t != focus_train]
        processed_trains = [t for t in processed_trains if t != focus_train]
        latest_agent_state["processed_trains"] = processed_trains
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
    train_number = str(data.get("train_number") or "").strip()
    if not train_number:
        raise HTTPException(status_code=400, detail="train_number is required")

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

    # The operator is watching this screen, so run the cycle inline and answer
    # with the incident it produced rather than making them guess whether the
    # injection landed. The cycle calls out to the reasoning model, so it is
    # bounded and degrades to "still running" instead of hanging the request.
    injected_at = datetime.utcnow()
    raised = None
    timed_out = False
    try:
        await asyncio.wait_for(run_single_agent_iteration(focus_train=train_number), timeout=60)
    except asyncio.TimeoutError:
        timed_out = True
    except Exception as e:
        print(f"[RAILMIND] Simulation cycle failed: {e}")

    try:
        raised = await find_incident_since(train_number, injected_at)
    except Exception as e:
        print(f"[RAILMIND] Could not look up the injected incident: {e}")

    return {
        "status": "anomaly_injected",
        "train_number": train_number,
        "delay_minutes": delay_minutes,
        "incident_raised": bool(raised),
        "incident": raised,
        "detail": (
            "Incident raised and queued for a decision." if raised
            else "Cycle still running — the incident will appear in Incident Alerts shortly."
            if timed_out
            else "No incident raised: this train did not breach any detection rule."
        ),
    }


async def find_incident_since(train_number: str, since: datetime):
    """Newest incident logged for a train after `since`, if any."""
    incidents = await db_client.get_incidents(limit=200)
    newest = None
    for inc in incidents:
        if str(inc.get("train_number")) != str(train_number):
            continue
        raised_at = triage_parse_time(inc.get("timestamp"))
        if raised_at is None or raised_at < since:
            continue
        if newest is None or raised_at > triage_parse_time(newest.get("timestamp")):
            newest = inc
    if not newest:
        return None
    return {
        "incident_id": newest.get("incident_id"),
        "incident_title": newest.get("incident_title"),
        "severity": newest.get("severity"),
        "situation_summary": newest.get("situation_summary"),
        "current_station": newest.get("current_station"),
        "delay_minutes": newest.get("delay_minutes"),
    }

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
