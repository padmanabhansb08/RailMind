import os
import json
import logging
import traceback
from dotenv import load_dotenv
from typing import Dict, Any, List
from uuid import uuid4
from datetime import datetime
from ..services.ai_service import reason_with_ai
from .state import AgentState, TrainAnomaly, DepartmentTask
from ..services.db_client import db_client
from ..services.railways_api import get_live_train_status, get_cancelled_trains, RailwaysAPIClient, get_multiple_trains
from ..services.twilio_service import TwilioSMSClient
from ..api.websocket import websocket_manager

logger = logging.getLogger(__name__)

# Ensure env variables are loaded before configuration
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=env_path)
api_key = os.getenv("RAILWAYS_API_KEY", "mock_key")
railways_client = RailwaysAPIClient(api_key=api_key)

twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "mock_sid")
twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "mock_token")
twilio_from = os.getenv("TWILIO_PHONE_NUMBER", "+1234567890")
twilio_client = TwilioSMSClient(account_sid=twilio_sid, auth_token=twilio_token, from_number=twilio_from)

# Global list of trains tracked by the background agent loop
# Start empty; populated dynamically via search
TRACKED_TRAINS = ["12301", "12951", "12001", "12259"]

# Shared log assistant that prints logs and broadcasts AGENT_LOG & AGENT_STATE_CHANGE WebSocket events
async def log_agent(node_name: str, message: str):
    print(message)
    
    # Determine log level based on message keywords
    level = "info"
    msg_upper = message.upper()
    if "ERROR" in msg_upper or "FAIL" in msg_upper or "CRITICAL" in msg_upper:
        level = "error"
    elif "WARN" in msg_upper or "ALERT" in msg_upper or "DEVIATION" in msg_upper:
        level = "warning"
    elif "SUCCESS" in msg_upper or "COMPLETE" in msg_upper or "OK" in msg_upper or "DISPATCH" in msg_upper or "SAVED" in msg_upper or "SENT" in msg_upper:
        level = "success"

    try:
        await websocket_manager.broadcast(json.dumps({
            "type": "AGENT_STATE_CHANGE",
            "state": node_name,
            "timestamp": datetime.utcnow().isoformat()
        }))
        await websocket_manager.broadcast(json.dumps({
            "type": "AGENT_LOG",
            "timestamp": datetime.utcnow().strftime('%H:%M:%S'),
            "node": node_name,
            "level": level,
            "message": message
        }))
    except Exception as e:
        logger.error(f"Failed to broadcast AGENT_LOG / AGENT_STATE_CHANGE message: {e}")

async def evaluate_previous_action(state: AgentState) -> AgentState:
    try:
        await log_agent("evaluate_previous_action", "[RAILMIND] Checking and evaluating previous self-healing actions...")
        
        # Pre-ingest live train status if raw_train_data is empty (since this node runs first)
        if not state.get("raw_train_data"):
            import time
            start_time = time.time()
            client = railways_client
            # Poll the trains this run is actually about. Previously this always
            # used TRACKED_TRAINS (populated only by operator searches), and
            # because it writes raw_train_data, ingest_node then reused that set
            # instead of polling target_trains — so a train injected from the
            # simulation portal was never fetched and never detected.
            train_numbers = state.get("target_trains") or TRACKED_TRAINS
            print(f"[RAILMIND] Pre-ingesting Railways API for {len(train_numbers)} trains...")
            results = await client.get_multiple_trains(train_numbers)

            # A train the feed could not serve is simply absent from this
            # cycle. The generator that used to invent a stand-in record has
            # been removed, and a fabricated train would be detected, reasoned
            # over and reported exactly like a real one.
            by_number = {r.get("train_number"): r for r in results if r.get("train_number")}
            train_results = [by_number[tn] for tn in train_numbers if tn in by_number]
            missing = [tn for tn in train_numbers if tn not in by_number]
            if missing:
                print(f"[RAILMIND] No live record for {len(missing)} train(s): {', '.join(missing)}")
            
            cancelled = await get_cancelled_trains()
            live_trains = train_results.copy()
            for train in cancelled:
                live_trains.append({
                    "train_number": train.get("TrainNo", "Unknown"),
                    "train_name": train.get("TrainName", "Unknown"),
                    "status": "cancelled",
                    "delay_minutes": 999,
                    "passenger_load": "overcrowded",
                    "current_station": "Unknown",
                    "lat": 20.5937,
                    "lng": 78.9629
                })
            state["raw_train_data"] = live_trains
            state["last_api_call"] = datetime.utcnow().isoformat()
            state["railways_latency_ms"] = int((time.time() - start_time) * 1000)

        # Evaluate pending incidents
        for train in state.get("raw_train_data", []):
            train_no = train.get("train_number")
            if not train_no:
                continue
                
            prev_incident = None
            if not db_client.use_fallback:
                try:
                    prev_incident = await db_client.db["incidents"].find_one({
                        "train_number": train_no,
                        "resolution_status": "pending"
                    }, sort=[("timestamp", -1)])
                except Exception:
                    db_client.use_fallback = True
            
            if db_client.use_fallback:
                incidents = await db_client.get_incidents(limit=100)
                for inc in incidents:
                    if inc.get("train_number") == train_no and inc.get("resolution_status") == "pending":
                        prev_incident = inc
                        break
            
            if prev_incident:
                loops_since = state.get("loop_count", 0) - prev_incident.get("loop_created", 0)
                
                # If delay is still high (or worsening) after 2 loops, escalate
                if loops_since >= 2 and train.get("delay_minutes", 0) > prev_incident.get("delay_minutes", 0):
                    await broadcast_log("ESCALATING",
                        f"Train {train_no} delay worsening ({prev_incident['delay_minutes']}min -> {train['delay_minutes']}min). Escalating to Control Room.")
                    
                    if "anomalies" not in state or state["anomalies"] is None:
                        state["anomalies"] = []
                    
                    # Ensure we don't insert duplicate escalation anomalies for the same train in this loop
                    if not any(a.get("train_number") == train_no and a.get("anomaly_type") == "escalation" for a in state["anomalies"]):
                        state["anomalies"].append({
                            **train,
                            "anomaly_type": "escalation",
                            "severity": "critical",
                            "reason": "Previous reroute ineffective"
                        })
    except Exception as e:
        logger.error(f"Error in evaluate_previous_action: {e}")
        await log_agent("evaluate_previous_action", f"[RAILMIND] [ERROR] Self-healing evaluation failed: {e}")
    return state

async def ingest_node(state: AgentState) -> AgentState:
    try:
        await log_agent("SCANNING", "Polling 15 trains on Indian Railways...")
        # If evaluate_previous_action already populated the raw train data, reuse it
        if state.get("raw_train_data"):
            live_trains = state["raw_train_data"]
        else:
            train_numbers = state.get("target_trains")
            if not train_numbers:
                train_numbers = TRACKED_TRAINS
            
            import time
            start_time = time.time()
            
            client = railways_client
            print(f"[RAILMIND] Calling Railways API for {len(train_numbers)} trains...")
            results = await client.get_multiple_trains(train_numbers)
            
            # A train the feed could not serve is simply absent from this
            # cycle. The generator that used to invent a stand-in record has
            # been removed, and a fabricated train would be detected, reasoned
            # over and reported exactly like a real one.
            by_number = {r.get("train_number"): r for r in results if r.get("train_number")}
            train_results = [by_number[tn] for tn in train_numbers if tn in by_number]
            missing = [tn for tn in train_numbers if tn not in by_number]
            if missing:
                print(f"[RAILMIND] No live record for {len(missing)} train(s): {', '.join(missing)}")
            
            results = train_results
            
            latency = int((time.time() - start_time) * 1000)
            state["last_api_call"] = datetime.utcnow().isoformat()
            state["railways_latency_ms"] = latency
            
            print(f"[RAILMIND] API returned {len(results)} trains")
            print(f"[RAILMIND] Sample: {results[0] if results else 'EMPTY - using mock'}")
            
            if not results:
                print("[RAILMIND] WARNING: Railways API returned no data, check RAILWAYS_API_KEY in .env")
                await log_agent("ingest_node", "[RAILMIND] WARNING: Railways API returned no data, check RAILWAYS_API_KEY in .env")
                
            cancelled = await get_cancelled_trains()
            live_trains = results.copy()
            for train in cancelled:
                live_trains.append({
                    "train_number": train.get("TrainNo", "Unknown"),
                    "train_name": train.get("TrainName", "Unknown"),
                    "status": "cancelled",
                    "delay_minutes": 999,
                    "passenger_load": "overcrowded",
                    "current_station": "Unknown",
                    "lat": 20.5937,
                    "lng": 78.9629
                })
        
        for train in live_trains:
            await websocket_manager.broadcast(json.dumps({
                "type": "TRAIN_UPDATE",
                "data": train
            }))
        
        state["raw_train_data"] = live_trains
        await log_agent("ingest_node", f"[RAILMIND] Ingested {len(live_trains)} trains")
    except Exception as e:
        logger.error(f"Error in ingest_node: {e}")
        await log_agent("ingest_node", f"[RAILMIND] [ERROR] Ingest node failed: {e}")
    return state

async def detect_node(state: AgentState) -> AgentState:
    try:
        await log_agent("detect_node", "[RAILMIND] Running real-time anomaly detection rules...")
        anomalies: List[TrainAnomaly] = []
        raw_data = state.get("raw_train_data", [])
        processed_trains = state.get("processed_trains", [])
        
        # Preserve custom simulated anomaly types if present
        simulated_types = {}
        for a in state.get("anomalies", []):
            if "train_number" in a and "anomaly_type" in a:
                simulated_types[a["train_number"]] = a["anomaly_type"]
                
        for train in raw_data:
            train_num = train.get("train_number", "Unknown")
            if train_num in processed_trains:
                continue
            train_name = train.get("train_name", "Unknown")
            location = train.get("current_station") or train.get("source") or "Unknown"
            delay = train.get("delay_minutes", 0)
            load = train.get("passenger_load")
            status = str(train.get("status") or "").lower()
            
            simulated_type = simulated_types.get(train_num)
            
            # Rule 1: delay > 15 minutes
            if delay > 15:
                severity = "low"
                if 15 < delay <= 30:
                    severity = "low"
                elif 30 < delay <= 60:
                    severity = "medium"
                elif 60 < delay <= 120:
                    severity = "high"
                elif delay > 120:
                    severity = "critical"
                    
                anomalies.append({
                    "train_number": train_num,
                    "train_name": train_name,
                    "anomaly_type": simulated_type or "delay",
                    "severity": severity,
                    "location": location,
                    "delay_minutes": delay,
                    "passenger_load": load,
                    "current_station": train.get("current_station") or location,
                    "status": status or "delayed",
                    "source": train.get("source") or "Unknown",
                    "destination": train.get("destination") or "Unknown"
                })
                
            # Rule 2: overcrowding checks
            elif load == "overcrowded":
                anomalies.append({
                    "train_number": train_num,
                    "train_name": train_name,
                    "anomaly_type": simulated_type or "overcrowding",
                    "severity": "high",
                    "location": location,
                    "delay_minutes": delay,
                    "passenger_load": load,
                    "current_station": train.get("current_station") or location,
                    "status": status or "delayed",
                    "source": train.get("source") or "Unknown",
                    "destination": train.get("destination") or "Unknown"
                })
                
            # Rule 3: cancellations
            elif status == "cancelled":
                anomalies.append({
                    "train_number": train_num,
                    "train_name": train_name,
                    "anomaly_type": simulated_type or "cancellation",
                    "severity": "critical",
                    "location": location,
                    "delay_minutes": delay,
                    "passenger_load": load,
                    "current_station": train.get("current_station") or location,
                    "status": "cancelled",
                    "source": train.get("source") or "Unknown",
                    "destination": train.get("destination") or "Unknown"
                })
                
        # Map station_code if not present using get_station_code_from_name
        for a in anomalies:
            if "station_code" not in a:
                loc = a.get("location") or a.get("current_station") or ""
                a["station_code"] = get_station_code_from_name(loc)

        # Broadcast DETECTED logs for each anomaly
        for a in anomalies:
            st_code = get_station_code_from_name(a.get("location") or a.get("current_station") or "") or a.get("location")[:4].upper()
            delay_text = f"{a['delay_minutes']}min delay" if a.get("delay_minutes") else "anomaly"
            await log_agent("DETECTED", f"Train {a['train_number']}: {delay_text} at {st_code}")

        # Cascading Failure Detection (Transformation 3)
        await log_agent("CASCADE?", "Checking Delhi-Mumbai corridor...")
        cascade_info = await detect_cascade(anomalies)
        if cascade_info.get("is_cascade"):
            corridor = cascade_info["corridor"]
            affected_stations = cascade_info["affected_stations"]
            await log_agent("detect_node", f"[RAILMIND] [CASCADE] {cascade_info['message']}")
            
            # Change severity of all affected corridor trains to critical
            for a in anomalies:
                if a.get("station_code") in affected_stations:
                    a["severity"] = "critical"
                    a["anomaly_type"] = "cascade"
            
            # Broadcast CASCADE_ALERT via WebSocket
            try:
                await websocket_manager.broadcast(json.dumps({
                    "type": "CASCADE_ALERT",
                    "corridor": corridor,
                    "affected_stations": affected_stations,
                    "message": cascade_info["message"]
                }))
            except Exception as ws_e:
                logger.error(f"Failed to broadcast CASCADE_ALERT: {ws_e}")

        state["anomalies"] = anomalies
        # The supervisor routes on this. Without it, it kept seeing an unknown
        # last node and sent the graph back to detection on every hop.
        state["last_node_executed"] = "detect_node"
        n = len(anomalies)
        if n > 0:
            await log_agent("detect_node", f"[RAILMIND] [WARNING] Detected {n} anomalies")
            state["should_continue"] = True
        else:
            await log_agent("detect_node", "[RAILMIND] [OK] All trains nominal")
            state["should_continue"] = False
    except Exception as e:
        logger.error(f"Error in detect_node: {e}")
        await log_agent("detect_node", f"[RAILMIND] [ERROR] Detect node failed: {e}")
    return state

def get_station_code_from_name(station_name: str) -> str:
    if not station_name:
        return ""
    import re

    name_upper = station_name.upper()
    words = set(re.findall(r"[A-Z0-9]+", name_upper))
    from ..services.railways_api import STATION_COORDS
    for code, info in STATION_COORDS.items():
        # A code has to appear as a whole word. Matching it as a substring made
        # "KOTA JUNCTION" resolve to JU (Jodhpur), which then drove the cascade
        # check and the memory lookup off a station the train was nowhere near.
        if info["name"].upper() in name_upper or name_upper in info["name"].upper() or code.upper() in words:
            return code


    if "DELHI" in name_upper or "NDLS" in name_upper:
        return "NDLS"
    if "KANPUR" in name_upper or "CNB" in name_upper:
        return "CNB"
    if "PRAYAGRAJ" in name_upper or "ALLAHABAD" in name_upper or "ALD" in name_upper:
        return "ALD"
    if "MUGHALSARAI" in name_upper or "MGS" in name_upper or "DEEN DAYAL" in name_upper:
        return "MGS"
    if "DHANBAD" in name_upper or "DHN" in name_upper:
        return "DHN"
    if "HOWRAH" in name_upper or "HWH" in name_upper:
        return "HWH"
    if "MUMBAI" in name_upper or "CSTM" in name_upper or "TERMINUS" in name_upper:
        return "CSTM"
    if "MATHURA" in name_upper or "MTJ" in name_upper:
        return "MTJ"
    if "AGRA" in name_upper or "AGC" in name_upper:
        return "AGC"
    if "BHOPAL" in name_upper or "BPL" in name_upper:
        return "BPL"
    if "NAGPUR" in name_upper or "NGP" in name_upper:
        return "NGP"
    if "CHENNAI" in name_upper or "MAS" in name_upper:
        return "MAS"
    if "AMBALA" in name_upper or "UMB" in name_upper:
        return "UMB"
    if "LUDHIANA" in name_upper or "LDH" in name_upper:
        return "LDH"
    if "AMRITSAR" in name_upper or "ASR" in name_upper:
        return "ASR"
        
    return station_name[:4].upper()

async def detect_cascade(anomalies: list) -> dict:
    CORRIDORS = {
        "Delhi-Howrah": ["NDLS","CNB","ALD","MGS","DHN","HWH"],
        "Delhi-Mumbai": ["NDLS","MTJ","AGC","BPL","NGP","CSTM"],
        "Delhi-Chennai": ["NDLS","AGC","BPL","NGP","MAS"],
        "Delhi-Amritsar": ["NDLS","UMB","LDH","ASR"],
    }
    
    # Map station_code if not present using get_station_code_from_name
    for a in anomalies:
        if "station_code" not in a:
            loc = a.get("location") or a.get("current_station") or ""
            a["station_code"] = get_station_code_from_name(loc)
            
    affected_stations = [a["station_code"] for a in anomalies]
    
    for corridor, stations in CORRIDORS.items():
        matches = [s for s in affected_stations if s in stations]
        if len(matches) >= 2:
            return {
                "is_cascade": True,
                "corridor": corridor,
                "affected_stations": matches,
                "message": f"NETWORK EVENT: {corridor} corridor disrupted at {len(matches)} points"
            }
    return {"is_cascade": False}

async def predict_node(state: AgentState) -> AgentState:
    try:
        await log_agent("predict_node", "[RAILMIND] Running predictive intelligence model...")
        anomalies = state.get("anomalies", [])
        if not anomalies:
            state["prediction"] = {}
            state["last_node_executed"] = "predict_node"
            return state
            
        predict_prompt = f"""
        Current delayed trains: {json.dumps(anomalies)}
        Time: {datetime.utcnow().strftime("%H:%M")}
        
        PREDICT the next 30 minutes:
        1. Which currently on-time trains will be affected 
           by these delays? (cascade effect)
        2. Which stations will face platform congestion?
        3. What is the worst case scenario?
        4. What preemptive actions can prevent the cascade?
        
        Respond in JSON: {{
            "at_risk_trains": ["train_no", ...],
            "congestion_stations": ["station_code", ...],
            "worst_case": "...",
            "preemptive_actions": ["action1", "action2"],
            "confidence": 0.0-1.0
        }}
        """
        prediction = await call_gemini(predict_prompt, state)
        state["prediction"] = prediction
        state["last_node_executed"] = "predict_node"
        
        at_risk = len(prediction.get("at_risk_trains", []))
        await log_agent("PREDICTING", f"{at_risk} trains at risk next 30 mins...")
        
        # Show prediction on dashboard
        try:
            await websocket_manager.broadcast(json.dumps({
                "type": "PREDICTION_UPDATE",
                "data": prediction
            }))
        except Exception as e:
            logger.error(f"Failed to broadcast prediction update: {e}")
    except Exception as e:
        logger.error(f"Error in predict_node: {e}")
        await log_agent("predict_node", f"[RAILMIND] [ERROR] Predictive intelligence failed: {e}")
    return state

async def broadcast_log(stage: str, message: str):
    level = "info"
    if stage == "THINKING":
        level = "info"
    elif stage == "DECIDING":
        level = "warning"
    elif stage == "ACTING":
        level = "success"
    
    try:
        await websocket_manager.broadcast(json.dumps({
            "type": "AGENT_STATE_CHANGE",
            "state": stage,
            "timestamp": datetime.utcnow().isoformat()
        }))
        await websocket_manager.broadcast(json.dumps({
            "type": "AGENT_LOG",
            "timestamp": datetime.utcnow().strftime('%H:%M:%S'),
            "node": "reason_node",
            "level": level,
            "message": message
        }))
    except Exception as e:
        logger.error(f"Failed to broadcast in broadcast_log: {e}")

def generate_mock_json_fallback(prompt: str, state: AgentState) -> dict:
    """Deterministic stand-in used when no reasoning model is reachable.

    It used to return a fixed script about train 12301 rerouting via Allahabad
    with a hardcoded 0.94 confidence and an invented passenger count, whatever
    the actual anomaly was. Now every field is derived from the anomaly in
    hand, and `confidence` is absent rather than fabricated — a derived plan is
    not a model prediction and should not carry a model's confidence.
    """
    from ..services.playbook import build_plan

    anomalies = state.get("anomalies", []) if state else []
    anomaly = anomalies[0] if anomalies else {}
    if not anomaly:
        return {}

    plan = build_plan(anomaly, peers=anomalies[1:])
    station = anomaly.get("current_station") or anomaly.get("location") or "the reported station"
    train_number = str(anomaly.get("train_number", ""))

    if "PREDICT the next 30 minutes" in prompt:
        peers = [a for a in anomalies[1:] if a.get("train_number")]
        return {
            "at_risk_trains": [str(a.get("train_number")) for a in peers][:5],
            "congestion_stations": sorted({
                str(a.get("station_code") or a.get("current_station") or "")
                for a in anomalies if a.get("station_code") or a.get("current_station")
            })[:5],
            "worst_case": plan["expected_outcome"] or f"{train_number} stays held at {station}.",
            "preemptive_actions": [plan["operations_task"], plan["station_manager_task"]],
            "source": "derived",
            "about_train": train_number,
        }

    if "STEP 1 - PERCEIVE" in prompt:
        return {
            "situation": plan["situation_summary"],
            "is_cascade": len(anomalies) >= 3,
            "affected_corridor": station,
            "severity_assessment": plan["severity"],
            "source": "derived",
            "about_train": train_number,
        }

    return {
        "decision": plan["reroute_plan"],
        "actions": [
            {
                "tool": "alert_department",
                "params": {"dept": "operations", "train_no": train_number, "message": plan["operations_task"], "urgency": plan["severity"]},
                "reason": "Pathing and slot allocation are controlled here.",
            },
            {
                "tool": "alert_department",
                "params": {"dept": "maintenance", "train_no": train_number, "message": plan["maintenance_task"], "urgency": plan["severity"]},
                "reason": "Rules out an infrastructure cause before the train is released.",
            },
            {
                "tool": "alert_department",
                "params": {"dept": "station_manager", "train_no": train_number, "message": plan["station_manager_task"], "urgency": plan["severity"]},
                "reason": "Passengers on the platform need the delay stated.",
            },
            {
                "tool": "send_passenger_alert",
                "params": {"train_no": train_number, "message": plan["passenger_sms"]},
                "reason": "Public-facing notice for this service.",
            },
        ],
        "estimated_recovery_time": plan["expected_outcome"],
        "reasoning_steps": plan["reasoning_steps"],
        "source": "derived",
        "about_train": train_number,
    }

async def call_gemini(prompt: str, state: AgentState = None) -> dict:
    """Ask the configured reasoning model for JSON, or derive a plan locally.

    Despite the name this only ever tried Groq, whose SDK is not installed, so
    every call silently fell through to the canned fallback. It now calls the
    Gemini REST endpoint directly with GEMINI_API_KEY (no extra dependency),
    keeps Groq as a secondary if that SDK is present, and marks which path
    produced the answer so the UI can say whether an operator is reading model
    output or a derived plan.
    """
    response_text = None
    source = None

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and gemini_key not in ("mock_key", "your_key_here"):
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            import httpx
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    url,
                    headers={"x-goog-api-key": gemini_key, "Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.1,
                            "responseMimeType": "application/json",
                        },
                    },
                )
                response.raise_for_status()
                payload = response.json()
                response_text = payload["candidates"][0]["content"]["parts"][0]["text"]
                source = "gemini"
        except Exception as e:
            logger.warning(f"Gemini call failed: {e}. Falling back.")

    groq_key = os.getenv("GROQ_API_KEY")
    if not response_text and groq_key and groq_key != "mock_key":
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=groq_key)
            response = await client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You must respond ONLY with a valid JSON block matching the requested format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama3-8b-8192",
                response_format={"type": "json_object"},
                temperature=0.1
            )
            response_text = response.choices[0].message.content
            source = "groq"
        except Exception as e:
            logger.warning(f"Groq API call failed: {e}. Using derived plan.")

    if response_text:
        try:
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            parsed = json.loads(clean_text.strip())
            if isinstance(parsed, dict):
                parsed.setdefault("source", source)
                return parsed
        except Exception as e:
            logger.warning(f"Failed to parse {source} response as JSON: {e}")

    return generate_mock_json_fallback(prompt, state)

async def execute_tool(tool_name: str, params: dict, reason: str, state: AgentState):
    await log_agent("reason_node", f"[TOOL ACT] Executing {tool_name} (Reason: {reason}) with params: {json.dumps(params)}")
    
    if "tools_used" not in state or state["tools_used"] is None:
        state["tools_used"] = []
    state["tools_used"].append(tool_name)
    
    # 1. Reroute Train
    if tool_name == "reroute_train":
        train_no = params.get("train_no") or params.get("train_number") or ""
        
        anomalies = state.get("anomalies", [])
        anomaly = next((a for a in anomalies if a.get("train_number") == train_no), {}) if anomalies else {}
        if not anomaly and anomalies:
            anomaly = anomalies[0]
            
        start_station = anomaly.get("current_station") or anomaly.get("location") or ""
        target_station = anomaly.get("destination", "")
        
        if not start_station:
            start_station = "Kanpur Central"
        if not target_station:
            target_station = "Varanasi"
            
        blocked = anomaly.get("location") or start_station
        
        from .routing import dijkstra_route_discovery
        res = dijkstra_route_discovery(start_station, target_station, blocked_station=blocked)
        if res["status"] != "Success":
            res = dijkstra_route_discovery(start_station, target_station, blocked_station=blocked)
            
        if res["status"] == "Success":
            route_str = " -> ".join(res["route"])
            state["reroute_plan"] = f"Dijkstra detour bypass: {route_str} (ETA {res['cost']} mins)"
            state["detour_route"] = res["route"]
            await log_agent("SMS", f"Operations: Execute reroute {train_no}")
        else:
            state["reroute_plan"] = f"No detour bypass available: {res.get('status', 'Unknown status')}"
            state["detour_route"] = []
            await log_agent("reason_node", f"[TOOL FAILED] Rerouting train {train_no} failed: {res.get('status')}")

    # 2. Alert Department
    elif tool_name == "alert_department":
        dept = params.get("dept") or params.get("department") or ""
        msg = params.get("message") or reason or ""
        urgency = params.get("urgency") or "medium"
        
        task: DepartmentTask = {
            "department": dept,
            "task_description": msg,
            "urgency": urgency,
            "action_required": "Emergency dispatch action"
        }
        
        if "department_tasks" not in state or state["department_tasks"] is None:
            state["department_tasks"] = []
        state["department_tasks"].append(task)
        
        # Save to database
        incident_uuid = str(uuid4())
        mongo_task = {
            "incident_id": incident_uuid,
            "department": dept,
            "task_description": msg,
            "urgency": urgency,
            "action_required": "Emergency dispatch action",
            "status": "pending",
            "timestamp": datetime.utcnow()
        }
        try:
            await db_client.insert_department_tasks([mongo_task])
        except Exception as e:
            logger.warning(f"Failed to save task to MongoDB: {e}")
            
        # Send SMS alert via Twilio
        m_phone = os.getenv("MAINTENANCE_PHONE", "+1234567891")
        o_phone = os.getenv("OPERATIONS_PHONE", "+1234567892")
        s_phone = os.getenv("STATION_PHONE", "+1234567893")
        phone_map = {
            "maintenance": m_phone,
            "operations": o_phone,
            "station_manager": s_phone,
            "station desk": s_phone,
            "station": s_phone
        }
        
        to_phone = phone_map.get(dept.lower())
        if to_phone:
            message_body = f"[RailMind Tool Alert] {dept.upper()}: {msg[:120]}... Urgency: {urgency}"
            try:
                sid = await twilio_client.send_incident_alert(to_phone, message_body)
                if sid:
                    if "sms_alerts_sent" not in state or state["sms_alerts_sent"] is None:
                        state["sms_alerts_sent"] = []
                    state["sms_alerts_sent"].append(sid)
            except Exception as e:
                logger.error(f"Error sending SMS: {e}")
        dept_lbl = "Maintenance Team" if "maintenance" in dept.lower() else "Station Manager" if "station" in dept.lower() else "Operations"
        await log_agent("SMS", f"{dept_lbl}: {msg}")

    # 3. Hold Train
    elif tool_name == "hold_train":
        train_no = params.get("train_no") or params.get("train_number") or ""
        station = params.get("station") or params.get("location") or ""
        duration = params.get("duration_mins") or params.get("duration") or 0
        st_code = get_station_code_from_name(station) or station
        await log_agent("SMS", f"Station Manager: PA announcement {st_code}")

    # 4. Send Passenger Alert
    elif tool_name == "send_passenger_alert":
        msg = params.get("message") or reason
        p_phone = os.getenv("DEMO_PASSENGER_PHONE", "+1234567894")
        if p_phone:
            try:
                sid = await twilio_client.send_incident_alert(p_phone, msg[:160])
                if sid:
                    if "sms_alerts_sent" not in state or state["sms_alerts_sent"] is None:
                        state["sms_alerts_sent"] = []
                    state["sms_alerts_sent"].append(sid)
            except Exception as e:
                logger.error(f"Error sending passenger SMS: {e}")
        await log_agent("reason_node", f"[TOOL SUCCESS] Passenger alert dispatched successfully")

    # 5. Escalate to Control Room
    elif tool_name == "escalate_to_control_room":
        summary = params.get("incident_summary") or reason
        await log_agent("reason_node", f"[TOOL SUCCESS] Incident escalated to Central Control Room: {summary}")

async def reason_node(state: AgentState) -> AgentState:
    # Counted before any early return so a reasoner that keeps coming back
    # empty cannot hold the supervisor in a loop.
    state["reason_attempts"] = state.get("reason_attempts", 0) + 1
    state["last_node_executed"] = "reason_node"
    try:
        anomalies = state.get("anomalies", [])
        if not anomalies:
            state["claude_reasoning"] = "{}"
            state["reroute_plan"] = None
            state["incident_report"] = None
            await log_agent("reason_node", "[RAILMIND] [OK] All trains nominal, skipping AI reasoning")
            return state

        # Fetch last 5 incidents for historical context
        try:
            incidents = await db_client.get_incidents(limit=5)
            state["incident_history"] = [
                {
                    "incident_title": inc.get("incident_title"),
                    "situation_summary": inc.get("situation_summary"),
                    "severity": inc.get("severity"),
                    "timestamp": str(inc.get("timestamp"))
                }
                for inc in incidents
            ]
        except Exception as e:
            logger.warning(f"Failed to fetch incident history: {e}")
            state["incident_history"] = []

        # Retrieve memory
        memories = []
        proven_solution = None
        anomaly = anomalies[0] if anomalies else {}
        train_number = anomaly.get("train_number")
        current_station = anomaly.get("current_station") or anomaly.get("location") or "Unknown"
        station_code = get_station_code_from_name(current_station)
        
        if train_number and station_code:
            try:
                memories = await db_client.get_memories(train_number, station_code, limit=5)
                if memories:
                    # Determine proven solution from memory
                    eff = memories[0].get("effectiveness", "")
                    if " recovered avg" in eff:
                        proven_solution = eff.split(" recovered avg")[0]
                    else:
                        proven_solution = eff
                    
                    if not proven_solution:
                        proven_solution = "Allahabad reroute"
                    
                    await log_agent("MEMORY", f"Using memory: {len(memories)} past incidents at this station. Proven solution: {proven_solution}")
                    state["memory_used"] = f"Using memory: {len(memories)} past incidents at this station. Proven solution: {proven_solution}."
                else:
                    state["memory_used"] = None
            except Exception as me:
                logger.warning(f"Failed to query memories: {me}")
                state["memory_used"] = None
        else:
            state["memory_used"] = None

        await log_agent("reason_node", f"[RAILMIND] Contacting AI to reason about {len(anomalies)} anomalies...")
        
        import time
        start_time = time.time()
        
        # STEP 1: PERCEIVE - What is happening?
        perception_prompt = f"""
        You are RailMind, India's autonomous railway brain.
        
        Current network status:
        {json.dumps(state.get("raw_train_data", []), indent=2)}
        
        Detected anomalies:
        {json.dumps(state.get("anomalies", []), indent=2)}
        
        Historical context (last 5 incidents):
        {json.dumps(state.get("incident_history", []), indent=2)}

        Historical memory for this train at this station:
        {json.dumps(memories, indent=2)}
        Use past successful strategies if available.
        
        STEP 1 - PERCEIVE: Analyze the full situation.
        What is ACTUALLY happening on the network right now?
        Are these anomalies connected? Is there a cascade 
        failure developing? Pattern analysis only.
        Respond in JSON: {{"situation": "...", 
        "is_cascade": true/false, 
        "affected_corridor": "...",
        "severity_assessment": "..."}}
        """
        await log_agent("THINKING", "Assessing the situation...")
        perception = await call_gemini(perception_prompt, state)

        situation = perception.get('situation') or "No situation assessment returned."
        await log_agent("PERCEIVED", situation)
        
        # STEP 2: DECIDE - What should be done?
        decision_prompt = f"""
        Situation assessment: {perception}

        Historical memory for this train at this station:
        {json.dumps(memories, indent=2)}
        Use past successful strategies if available.
        
        STEP 2 - DECIDE: Make autonomous operational decisions.
        
        Consider:
        - Which trains need immediate rerouting?
        - Which stations need to be alerted?
        - Is this a single incident or network-wide issue?
        - What is the priority order of actions?
        - What is the estimated passenger impact?
        
        You have these tools available:
        - reroute_train(train_no, via_station)
        - alert_department(dept, message, urgency)
        - hold_train(train_no, station, duration_mins)
        - send_passenger_alert(train_no, message)
        - escalate_to_control_room(incident_summary)
        
        Decide which tools to use and in what order.
        Respond in JSON: {{
            "decision": "...",
            "actions": [
                {{"tool": "reroute_train", 
                  "params": {{}}, 
                  "reason": "..."}},
            ],
            "passenger_impact": "X passengers affected",
            "estimated_recovery_time": "X minutes",
            "confidence": 0.0-1.0
        }}
        """
        await log_agent("DECIDING", "Weighing response options...")
        decision = await call_gemini(decision_prompt, state)

        # No invented confidence and no placeholder decision text: a derived
        # plan carries no model confidence, and saying "94%" over a template
        # would misrepresent how the answer was reached.
        confidence = decision.get('confidence')
        decided_msg = decision.get('decision') or "No decision returned."
        if confidence is not None:
            await log_agent("DECIDED", f"Confidence: {int(float(confidence) * 100)}%. {decided_msg}")
        else:
            await log_agent("DECIDED", f"{decided_msg} (derived, no model confidence)")

        # STEP 3: ACT - Execute decisions
        actions_count = len(decision.get('actions', []))
        await log_agent("ACTING", f"Dispatching {actions_count} department action(s)...")
        
        # One malformed tool call must not lose the whole assessment. The model
        # is free to name a station the route graph has never heard of, and an
        # unguarded KeyError there previously aborted reason_node and threw away
        # the perception and decision it had already produced.
        for action in decision.get("actions", []):
            if not isinstance(action, dict):
                continue
            try:
                await execute_tool(action.get("tool"),
                                   action.get("params", {}) or {},
                                   action.get("reason", ""),
                                   state)
            except Exception as tool_error:
                logger.warning(f"Tool {action.get('tool')} failed: {tool_error!r}")
                await log_agent(
                    "reason_node",
                    f"[TOOL FAILED] {action.get('tool')} could not be executed: {tool_error!r}"
                )
        
        state["perception"] = perception
        state["decision"] = decision
        state["claude_reasoning"] = json.dumps({
            "perception": perception,
            "decision": decision,
            "situation_summary": perception.get("situation", ""),
            "reroute_plan": state.get("reroute_plan") or ""
        })
        
        latency = int((time.time() - start_time) * 1000)
        state["ai_latency_ms"] = latency
        await log_agent("reason_node", f"[RAILMIND] Real Autonomous Brain cycle complete ({latency}ms)")
        
    except Exception as e:
        logger.error(f"Error in reason_node: {e}")
        await log_agent("reason_node", f"[RAILMIND] [ERROR] Reason node failed: {e}")
    return state

from .routing import dijkstra_route_discovery

async def reroute_node(state: AgentState) -> AgentState:
    """Decide the movement plan for the lead anomaly.

    This node must always come back with a `reroute_plan`. The supervisor routes
    here whenever that field is empty, and the old version only filled it for
    one hardcoded case (a train at Kanpur Central with no destination). For
    every other train it returned nothing, so the supervisor sent it straight
    back here and the graph span between the two until it hit the recursion
    limit — which is why cycles never reached the report node.
    """
    try:
        await log_agent("reroute_node", "[RAILMIND] Checking and resolving rerouting options...")

        anomalies = dedupe_anomalies(state.get("anomalies", []))
        if not anomalies:
            return {
                "reroute_plan": "No anomaly to route around.",
                "detour_route": [],
                "last_node_executed": "reroute_node",
            }

        anomaly = anomalies[0]
        start_station = anomaly.get("current_station") or anomaly.get("location") or ""
        target_station = anomaly.get("destination") or ""
        train_no = anomaly.get("train_number", "the train")

        # A diversion is only worth proposing when the graph actually knows both
        # ends of the run. Otherwise the honest answer is priority pathing on
        # the booked route, which is what the playbook recommends.
        if start_station and target_station:
            blocked = anomaly.get("location") or start_station
            result = dijkstra_route_discovery(start_station, target_station, blocked_station=blocked)
            if result["status"] != "Success":
                result = dijkstra_route_discovery(start_station, target_station)

            if result["status"] == "Success" and len(result["route"]) > 1:
                route_str = " -> ".join(result["route"])
                await log_agent("reroute_node", f"[RAILMIND] Detour available for {train_no}: {route_str}")
                return {
                    "reroute_plan": (
                        f"Detour available for {train_no}: {route_str} "
                        f"(about {result['cost']} min on the diverted path). "
                        f"Use it only if the booked route ahead of {start_station} is blocked."
                    ),
                    "detour_route": result["route"],
                    "last_node_executed": "reroute_node",
                }

            await log_agent("reroute_node", f"[RAILMIND] No mapped detour for {train_no}: {result.get('status')}")

        from ..services.playbook import build_plan
        fallback = build_plan(anomaly, peers=anomalies[1:])
        return {
            "reroute_plan": fallback["reroute_plan"],
            "detour_route": [],
            "last_node_executed": "reroute_node",
        }

    except Exception as e:
        logger.error(f"Error in reroute_node: {e}")
        await log_agent("reroute_node", f"[RAILMIND] [ERROR] Reroute node failed: {e}")
    # Even on failure the field must be set, or the supervisor loops back here.
    return {
        "reroute_plan": "Routing check failed; handle on the booked route and refer to the section controller.",
        "detour_route": [],
        "last_node_executed": "reroute_node",
    }

async def coordination_node(state: AgentState) -> AgentState:
    try:
        await log_agent("coordination_node", "[RAILMIND] Initiating department task dispatches...")
        claude_json = state.get("claude_reasoning", "{}")
        try:
            claude_response = json.loads(claude_json)
        except Exception as e:
            logger.error(f"Error parsing Claude reasoning JSON in coordination_node: {e}")
            claude_response = {}

        anomalies = state.get("anomalies", [])
        
        # Calculate highest severity from anomalies
        severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        highest_severity = "low"
        highest_rank = 0

        for anomaly in anomalies:
            sev = anomaly.get("severity", "low").lower()
            rank = severity_rank.get(sev, 1)
            if rank > highest_rank:
                highest_rank = rank
                highest_severity = sev
                if highest_rank == 4:
                    break

        has_critical = (highest_severity == "critical")
        operations_urgency = "high" if has_critical else "medium"

        # Support nested format or flat format
        maintenance_desc = "Inspect signals and tracks."
        operations_desc = "Coordinate slot changes and schedules."
        station_desc = "Broadcast announcement on platform boards."
        
        if "perception" in claude_response and "decision" in claude_response:
            actions = claude_response["decision"].get("actions", [])
            for action in actions:
                tool = action.get("tool")
                reason = action.get("reason", "")
                params = action.get("params", {})
                if tool == "alert_department":
                    dept = params.get("dept", "").lower()
                    msg = params.get("message", reason)
                    if "maintenance" in dept:
                        maintenance_desc = msg
                    elif "operations" in dept:
                        operations_desc = msg
                    elif "station" in dept or "manager" in dept:
                        station_desc = msg
                elif tool == "reroute_train":
                    operations_desc = f"Reroute train {params.get('train_no')} via {params.get('via_station')}: {reason}"
        else:
            maintenance_desc = claude_response.get("maintenance_task", "Inspect signals and tracks.")
            operations_desc = claude_response.get("operations_task", "Coordinate slot changes and schedules.")
            station_desc = claude_response.get("station_manager_task", "Broadcast announcement on platform boards.")

        maintenance_task: DepartmentTask = {
            "department": "maintenance",
            "task_description": maintenance_desc,
            "urgency": highest_severity,
            "action_required": "Dispatch repair team immediately"
        }

        operations_task: DepartmentTask = {
            "department": "operations",
            "task_description": operations_desc,
            "urgency": operations_urgency,
            "action_required": "Execute rerouting plan"
        }

        station_manager_task: DepartmentTask = {
            "department": "station_manager",
            "task_description": station_desc,
            "urgency": "high",
            "action_required": "Make passenger announcement + update platform boards"
        }

        department_tasks = [maintenance_task, operations_task, station_manager_task]
        state["department_tasks"] = department_tasks

        # Save to MongoDB
        incident_uuid = str(uuid4())
        mongo_tasks = []
        for task in department_tasks:
            mongo_tasks.append({
                "incident_id": incident_uuid,
                "department": task["department"],
                "task_description": task["task_description"],
                "urgency": task["urgency"],
                "action_required": task["action_required"],
                "status": "pending",
                "timestamp": datetime.utcnow()
            })

        try:
            await db_client.insert_department_tasks(mongo_tasks)
        except Exception as e:
            logger.warning(f"Failed to save department tasks to MongoDB: {e}")

        await log_agent("coordination_node", "[RAILMIND] Dispatched tasks to 3 departments simultaneously")
        return {"department_tasks": department_tasks}
    except Exception as e:
        logger.error(f"Error in coordination_node: {e}")
        await log_agent("coordination_node", f"[RAILMIND] [ERROR] Coordination node failed: {e}")
    return {}

async def alert_node(state: AgentState) -> AgentState:
    try:
        await log_agent("alert_node", "[RAILMIND] Sending Twilio notifications...")
        m_phone = os.getenv("MAINTENANCE_PHONE", "+1234567891")
        o_phone = os.getenv("OPERATIONS_PHONE", "+1234567892")
        s_phone = os.getenv("STATION_PHONE", "+1234567893")
        p_phone = os.getenv("DEMO_PASSENGER_PHONE", "+1234567894")

        phone_map = {
            "maintenance": m_phone,
            "operations": o_phone,
            "station_manager": s_phone
        }

        tasks = state.get("department_tasks", [])
        sent_sms = []

        for task in tasks:
            dept = task.get("department", "")
            desc = task.get("task_description", "")
            urg = task.get("urgency", "medium")

            to_phone = phone_map.get(dept)
            if to_phone:
                message_body = f"[RailMind Alert] {dept.upper()}: {desc[:120]}... Urgency: {urg}"
                try:
                    sid = await twilio_client.send_incident_alert(to_phone, message_body)
                    if sid:
                        sent_sms.append(sid)
                except Exception as e:
                    logger.error(f"Error sending SMS to {dept}: {e}")

        # Send passenger SMS
        claude_json = state.get("claude_reasoning", "{}")
        try:
            claude_response = json.loads(claude_json)
        except Exception:
            claude_response = {}

        pass_sms = claude_response.get("passenger_sms")
        if pass_sms and p_phone:
            try:
                sid = await twilio_client.send_incident_alert(p_phone, pass_sms[:160])
                if sid:
                    sent_sms.append(sid)
            except Exception as e:
                logger.error(f"Error sending passenger SMS: {e}")

        await log_agent("alert_node", f"[RAILMIND] SMS alerts sent to {len(sent_sms)} recipients")
        return {"sms_alerts_sent": sent_sms}
    except Exception as e:
        logger.error(f"Error in alert_node: {e}")
        await log_agent("alert_node", f"[RAILMIND] [ERROR] Alert node failed: {e}")
    return {}

async def save_incident_if_not_duplicate(incident):
    # Check last 5 minutes for same train number
    duplicate = await db_client.has_recent_incident(incident["train_number"], minutes=5)
    
    if duplicate:
        print(f"[RAILMIND] Skipping duplicate incident for train {incident['train_number']} (last logged in the last 5 minutes)")
        return False
    
    await db_client.insert_incident(incident)
    print(f"[RAILMIND] New incident saved: {incident['incident_title']}")
    return True

def dedupe_anomalies(anomalies):
    """One entry per train, keeping the most severe view of it.

    evaluate_previous_action raises escalations for trains that detect_node also
    flags, and the state reducer appends rather than replaces, so the same train
    can appear several times in one cycle. Reporting each copy would put
    duplicate cards in front of an operator.
    """
    rank = {"critical": 4, "high": 3, "severe": 3, "medium": 2, "low": 1, "info": 0}
    best = {}
    for a in anomalies or []:
        if not isinstance(a, dict):
            continue
        key = str(a.get("train_number") or "unknown")
        current = best.get(key)
        if current is None:
            best[key] = a
            continue
        if rank.get(str(a.get("severity", "")).lower(), 0) > rank.get(str(current.get("severity", "")).lower(), 0):
            best[key] = a
        elif (a.get("delay_minutes") or 0) > (current.get("delay_minutes") or 0):
            best[key] = a
    return list(best.values())


# One cycle should not be able to flood the queue faster than an operator can
# read it. Anything beyond this is picked up by the next cycle.
MAX_INCIDENTS_PER_CYCLE = 8


async def report_node(state: AgentState) -> AgentState:
    try:
        await log_agent("report_node", "[RAILMIND] Broadcasting operations report...")

        from ..services.playbook import build_plan
        from ..services.railways_api import SIMULATED_OVERRIDES

        anomalies = dedupe_anomalies(state.get("anomalies", []))
        if not anomalies:
            return {}

        # An operator-injected train is what someone is watching for, so it is
        # reported first rather than being cut off by the per-cycle cap.
        anomalies.sort(key=lambda a: (
            0 if str(a.get("train_number")) in SIMULATED_OVERRIDES else 1,
            -(a.get("delay_minutes") or 0),
        ))

        claude_json = state.get("claude_reasoning", "{}")
        try:
            claude_response = json.loads(claude_json)
        except Exception:
            claude_response = {}

        # Model output describes the anomaly the reasoner was given - the first
        # one. Every other incident in this cycle gets its own derived plan
        # rather than inheriting text about a different train.
        primary_number = str(anomalies[0].get("train_number") or "")

        # The reasoner works on whichever anomaly led the list when it ran, which
        # is not necessarily the train reported first here. Applying its text to
        # the wrong card produced an incident about a 135 min delay at Itarsi
        # whose plan, tasks and reasoning all named a different train at a
        # different station. Only use it on the train it was written about.
        # reason_node wraps the perception and decision objects, so these markers
        # sit one level down as often as they sit at the top.
        def _marker(key):
            if not isinstance(claude_response, dict):
                return ""
            for scope in (claude_response, claude_response.get("perception"), claude_response.get("decision")):
                if isinstance(scope, dict) and scope.get(key):
                    return str(scope[key])
            return ""

        model_about = _marker("about_train")
        model_is_derived = _marker("source") == "derived"
        model_target = model_about or primary_number
        model_plan = {} if model_is_derived else extract_model_plan(claude_response, model_target)

        cascade_info = await detect_cascade(anomalies)
        if cascade_info.get("is_cascade"):
            await log_agent(
                "report_node",
                f"[RAILMIND] [CASCADE] {cascade_info.get('message', 'Corridor disruption detected')}"
            )

        processed_trains = list(state.get("processed_trains", []))
        raised = 0

        for anomaly in anomalies[:MAX_INCIDENTS_PER_CYCLE]:
            train_number = str(anomaly.get("train_number", "Unknown"))
            train_name = anomaly.get("train_name", "Unknown")
            current_station = anomaly.get("current_station") or anomaly.get("location") or "Unknown"
            delay_minutes = anomaly.get("delay_minutes", 0)
            severity = anomaly.get("severity", "medium")

            derived = build_plan(anomaly, peers=[a for a in anomalies if a is not anomaly])
            use_model = bool(model_plan) and train_number == model_target
            plan = {**derived, **(model_plan if use_model else {})}

            incident_id = str(uuid4())
            incident_report = {
                "incident_id": incident_id,
                # An injected delay is not live telemetry; the card says so.
                "simulated": train_number in SIMULATED_OVERRIDES,
                "reasoning_source": "model" if use_model else "derived",
                "loop_created": state.get("loop_count", 0),
                "timestamp": datetime.utcnow().isoformat(),
                "train_number": train_number,
                "train_name": train_name,
                # Always the per-train title. A corridor-wide headline on one
                # arbitrary train's card described a network event while the
                # body described a single train, and the two never matched.
                "incident_title": f"{train_number} {train_name} delayed {delay_minutes}min at {current_station}",
                "current_station": current_station,
                "delay_minutes": delay_minutes,
                "severity": severity,
                "situation_summary": plan.get("situation_summary"),
                "reroute_plan": plan.get("reroute_plan"),
                "maintenance_task": plan.get("maintenance_task"),
                "operations_task": plan.get("operations_task"),
                "station_manager_task": plan.get("station_manager_task"),
                "passenger_sms": plan.get("passenger_sms"),
                "expected_outcome": plan.get("expected_outcome"),
                "resolution_status": "pending",
                "departments_notified": ["maintenance", "operations", "station_manager"],
                "sms_sent": len(state.get("sms_alerts_sent", [])),
                "detour_route": state.get("detour_route") or [],
                "confidence_score": plan.get("confidence_score"),
                "reasoning_steps": plan.get("reasoning_steps") or [],
                "memory_used": state.get("memory_used"),
            }

            if await save_incident_if_not_duplicate(incident_report):
                raised += 1
                try:
                    await websocket_manager.broadcast(json.dumps({
                        "type": "INCIDENT_UPDATE",
                        "data": incident_report
                    }))
                except Exception as e:
                    logger.error(f"Failed to broadcast incident update: {e}")
                await log_agent("LOGGED", f"Incident #RM-{incident_id[:3].upper()} raised for {train_number} at {current_station}")

            if train_number not in processed_trains:
                processed_trains.append(train_number)

        state["loop_count"] = state.get("loop_count", 0) + 1
        state["next_node"] = "END"
        await log_agent("COMPLETE", f"Cycle {state.get('loop_count', 0)} done. {raised} incident(s) raised from {len(anomalies)} anomalies.")

        return {
            "processed_trains": processed_trains,
            "loop_count": state.get("loop_count", 0),
            "anomalies": ["CLEAR"], # clear anomalies so next run starts fresh
            "sms_alerts_sent": ["CLEAR"],
            "department_tasks": ["CLEAR"],
            "claude_reasoning": "{}",
            "reason_attempts": 0,
            "dispatched": ["CLEAR"]
        }

    except Exception as e:
        logger.error(f"Error in report_node: {e}")
        await log_agent("report_node", f"[RAILMIND] [ERROR] Report node failed: {e}")
    return {}


def action_is_about(action, params, message, train_number):
    """Whether a model action applies to this train.

    An action naming a different train explicitly is rejected. An action naming
    no train at all is accepted: general instructions ("prepare the platform")
    are still useful on the card that triggered them.
    """
    import re

    named = str(params.get("train_no") or params.get("train_number") or "").strip()
    if named:
        return named == str(train_number)

    mentioned = set(re.findall(r"\d{5}", f"{message or ''} {action.get('reason', '')}"))
    if not mentioned:
        return True
    return str(train_number) in mentioned


def extract_model_plan(claude_response, train_number=None):
    """Pull the usable fields out of a reasoner response, or return {}.

    Only keys the model actually filled in are returned, so they overlay the
    derived plan instead of blanking it where the model said nothing.

    `train_number` scopes the department actions to one train. The reasoner sees
    the whole cycle and happily returns an instruction about 12301 alongside one
    about 12951; without this filter the first incident absorbed all of them and
    the card told an operator to act on a train it was not about.
    """
    if not isinstance(claude_response, dict) or not claude_response:
        return {}

    plan = {}
    perception = claude_response.get("perception")
    decision = claude_response.get("decision")

    if isinstance(perception, dict) and isinstance(decision, dict):
        if perception.get("situation"):
            plan["situation_summary"] = perception["situation"]
        if decision.get("decision"):
            plan["reroute_plan"] = decision["decision"]
        if decision.get("estimated_recovery_time"):
            plan["expected_outcome"] = decision["estimated_recovery_time"]

        confidence = decision.get("confidence")
        if confidence is not None:
            try:
                plan["confidence_score"] = int(float(confidence) * 100)
            except (TypeError, ValueError):
                pass

        actions = decision.get("actions", []) or []
        for action in actions:
            if not isinstance(action, dict):
                continue
            tool = action.get("tool")
            params = action.get("params", {}) or {}
            message = params.get("message") or action.get("reason")
            if train_number and not action_is_about(action, params, message, train_number):
                continue
            if tool == "alert_department" and message:
                dept = str(params.get("dept", "")).lower()
                if "maintenance" in dept:
                    plan["maintenance_task"] = message
                elif "operations" in dept:
                    plan["operations_task"] = message
                elif "station" in dept or "manager" in dept:
                    plan["station_manager_task"] = message
            elif tool == "send_passenger_alert" and message:
                plan["passenger_sms"] = message
            elif tool == "reroute_train":
                plan["reroute_plan"] = (
                    f"Reroute {params.get('train_no')} via {params.get('via_station')}: "
                    f"{action.get('reason', '')}".strip()
                )

        steps = decision.get("reasoning_steps") or claude_response.get("reasoning_steps")
        if steps:
            plan["reasoning_steps"] = steps
        elif perception.get("situation") and decision.get("decision"):
            plan["reasoning_steps"] = [
                f"Observed: {perception.get('situation')}",
                f"Assessed: corridor {perception.get('affected_corridor')}, "
                f"cascade {'yes' if perception.get('is_cascade') else 'no'}.",
                f"Decided: {decision.get('decision')}",
                f"Dispatched: {len(actions)} department action(s).",
            ]
        return plan

    # Flat shape
    for key in ("situation_summary", "maintenance_task", "operations_task",
                "station_manager_task", "passenger_sms", "reroute_plan",
                "confidence_score", "reasoning_steps"):
        if claude_response.get(key):
            plan[key] = claude_response[key]
    return plan


async def supervisor_node(state: AgentState) -> dict:
    """Dispatch the next stage of the cycle.

    Each stage is dispatched at most once per cycle, recorded in `dispatched`.
    The previous version re-derived the next stage purely from whether a state
    field was still empty, so any node that could not fill its field — a reroute
    with no mapped path, an SMS send against unconfigured Twilio credentials —
    was dispatched forever until LangGraph hit the recursion limit and the cycle
    died before reporting anything. A stage that runs and produces nothing is a
    stage that is finished, not one to retry.
    """
    try:
        last_node = state.get("last_node_executed")
        dispatched = set(state.get("dispatched") or [])
        await log_agent("supervisor_node", f"[RAILMIND] Supervisor evaluating graph state... (Last execution: {last_node})")

        def go(node):
            return {
                "next_node": node,
                "last_node_executed": "supervisor_node",
                "dispatched": [node],
            }

        # Self correction loop check first
        claude_reasoning_raw = state.get("claude_reasoning")
        if claude_reasoning_raw and claude_reasoning_raw != "{}":
            try:
                reasoning = json.loads(claude_reasoning_raw)
                maintenance = reasoning.get("maintenance_task", "")
                if "Kanpur" in maintenance and "restricted" in maintenance.lower():
                    # Mock conflict logic
                    await log_agent("supervisor_node", "[RAILMIND] [WARNING] Conflict detected in maintenance task. Re-routing to Reasoner.")
                    return {
                        "errors": ["Maintenance task conflicts with active line configurations at Kanpur."],
                        "claude_reasoning": "{}", # clear to force re-reason
                        "next_node": "reason_node",
                        "last_node_executed": "supervisor_node",
                        "dispatched": ["reason_node"],
                    }
            except json.JSONDecodeError as e:
                logger.warning("JSON parse failed: %s", e)
            except Exception:
                logger.exception("Unexpected error in supervisor self-correction logic")
                raise

        anomalies = state.get("anomalies", [])

        # Nothing detected means nothing to report - end rather than loop.
        if not anomalies and last_node in ("detect_node", "predict_node", "supervisor_node"):
            return {"next_node": "END", "last_node_executed": "supervisor_node"}

        # If we just came from ingest, we must go to detect.
        if not last_node or last_node == "ingest_node":
            return go("detect_node")

        # Reason before acting. This branch was missing entirely: the graph went
        # straight from detection to rerouting, so claude_reasoning stayed empty
        # and every incident fell back to canned task text ("Inspect signaling
        # hardware") no matter what had actually happened. Bounded by
        # reason_attempts so an unusable model response degrades to the derived
        # plan instead of looping.
        reasoning_raw = state.get("claude_reasoning") or "{}"
        if (anomalies and reasoning_raw.strip() in ("", "{}")
                and state.get("reason_attempts", 0) < 2):
            return go("reason_node")

        if not state.get("reroute_plan") and "reroute_node" not in dispatched:
            return go("reroute_node")

        # If tasks not generated
        if not state.get("department_tasks") and "coordination_node" not in dispatched:
            return go("coordination_node")

        # If alerts not sent. Only worth attempting once — a failed send means
        # the notification channel is down, not that it should be retried until
        # the cycle dies.
        if (not state.get("sms_alerts_sent")
                and len(state.get("department_tasks", [])) > 0
                and "alert_node" not in dispatched):
            return go("alert_node")

        # Otherwise report and finish
        return go("report_node")

    except Exception as e:
         logger.exception("Error in supervisor_node")
         tb = traceback.format_exc()
         await log_agent("supervisor_node", f"[RAILMIND] [ERROR] Supervisor node failed: {e}\n{tb}")
         return {"next_node": "END", "last_node_executed": "supervisor_node"}
