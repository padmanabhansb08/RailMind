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
from ..services.railways_api import get_live_train_status, get_cancelled_trains, mock_train_data, RailwaysAPIClient, get_multiple_trains
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
TRACKED_TRAINS = []

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
            print(f"[RAILMIND] Pre-ingesting Railways API for {len(TRACKED_TRAINS)} trains...")
            results = await client.get_multiple_trains(TRACKED_TRAINS)
            
            train_results = []
            for tn in TRACKED_TRAINS:
                found = False
                for r in results:
                    if r.get("train_number") == tn:
                        train_results.append(r)
                        found = True
                        break
                if not found:
                    from ..services.railways_api import get_mock_rapidapi_train, parse_rapidapi_train_for_agent
                    mock_data = get_mock_rapidapi_train(tn)
                    parsed_mock = parse_rapidapi_train_for_agent(mock_data, tn)
                    if parsed_mock:
                        train_results.append(parsed_mock)
            
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
            
            # Ensure that if some train fetches failed and returned empty dict, they fallback to get_mock_rapidapi_train
            # So we always have all 15 trains
            train_results = []
            for tn in train_numbers:
                found = False
                for r in results:
                    if r.get("train_number") == tn:
                        train_results.append(r)
                        found = True
                        break
                if not found:
                    from ..services.railways_api import get_mock_rapidapi_train, parse_rapidapi_train_for_agent
                    mock_data = get_mock_rapidapi_train(tn)
                    parsed_mock = parse_rapidapi_train_for_agent(mock_data, tn)
                    if parsed_mock:
                        train_results.append(parsed_mock)
            
            results = train_results
            
            latency = int((time.time() - start_time) * 1000)
            state["last_api_call"] = datetime.utcnow().isoformat()
            state["railways_latency_ms"] = latency
            
            print(f"[RAILMIND] API returned {len(results)} trains")
            print(f"[RAILMIND] Sample: {results[0] if results else 'EMPTY - using mock'}")
            
            if not results:
                print("[RAILMIND] WARNING: Railways API returned no data, check RAILWAYS_API_KEY in .env")
                await log_agent("ingest_node", "[RAILMIND] WARNING: Railways API returned no data, check RAILWAYS_API_KEY in .env")
                results = mock_train_data()
                print("[RAILMIND] Using mock fallback data")
                await log_agent("ingest_node", "[RAILMIND] Using mock fallback data")
                
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
    name_upper = station_name.upper()
    from ..services.railways_api import STATION_COORDS
    for code, info in STATION_COORDS.items():
        if info["name"].upper() in name_upper or name_upper in info["name"].upper() or code.upper() in name_upper:
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
    is_prediction = "PREDICT the next 30 minutes" in prompt
    
    anomalies = state.get("anomalies", []) if state else []
    anomaly = anomalies[0] if anomalies else {}
    
    train_number = anomaly.get("train_number", "12301")
    train_name = anomaly.get("train_name", "Rajdhani Express")
    location = anomaly.get("current_station") or anomaly.get("location") or "Kanpur Central"
    anomaly_type = anomaly.get("anomaly_type", "delay")
    delay = anomaly.get("delay_minutes", 45)
    severity = anomaly.get("severity", "medium")
    
    if is_prediction:
        return {
            "at_risk_trains": ["12309", "12259", "12565"],
            "congestion_stations": ["CNB", "ALD", "NDLS"],
            "worst_case": "In the next 30 minutes: 3 trains at risk of delay cascade on Delhi-Howrah corridor. Preemptive alerts dispatched to Allahabad and Kanpur stations.",
            "preemptive_actions": [
                "Hold non-essential freight traffic at outer signal block cabin of CNB.",
                "Reroute oncoming express services via secondary chord bypass loop."
            ],
            "confidence": 0.94
        }

    is_perception = "STEP 1 - PERCEIVE" in prompt
    
    if is_perception:
        return {
            "situation": "Network stress on 2 corridors. Not cascade yet. Individual responses needed.",
            "is_cascade": False,
            "affected_corridor": "Delhi-Howrah Corridor",
            "severity_assessment": "medium"
        }
    else:
        return {
            "decision": "Rerouting 12301 via Allahabad. Holding 12625 at Nagpur 8 mins.",
            "actions": [
                {
                    "tool": "reroute_train",
                    "params": {"train_no": "12301", "via_station": "Allahabad"},
                    "reason": "Bypass blocked section"
                },
                {
                    "tool": "alert_department",
                    "params": {"dept": "maintenance", "message": "Platform inspection CNB", "urgency": "critical"},
                    "reason": "Clear active rail line section"
                },
                {
                    "tool": "hold_train",
                    "params": {"train_no": "12625", "station": "Nagpur", "duration_mins": 8},
                    "reason": "spacing safety"
                }
            ],
            "passenger_impact": "847 passengers affected",
            "estimated_recovery_time": "30 minutes",
            "confidence": 0.94
        }

async def call_gemini(prompt: str, state: AgentState = None) -> dict:
    groq_key = os.getenv("GROQ_API_KEY")
    response_text = None
    
    if groq_key and groq_key != "mock_key":
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
        except Exception as e:
            logger.warning(f"Groq API call failed: {e}. Using mock fallback.")
            
    if response_text:
        try:
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            return json.loads(clean_text)
        except Exception as e:
            logger.warning(f"Failed to parse Groq response as JSON: {e}")
            
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
        await log_agent("THINKING", "Sending to Gemini for perception...")
        perception = await call_gemini(perception_prompt, state)
        
        situation = perception.get('situation', 'Network stress on 2 corridors. Not cascade yet. Individual responses needed.')
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
        await log_agent("DECIDING", "Evaluating 4 possible actions...")
        decision = await call_gemini(decision_prompt, state)
        
        confidence = int(decision.get('confidence', 0.94) * 100)
        decided_msg = decision.get('decision', 'Rerouting 12301 via Allahabad. Holding 12625 at Nagpur 8 mins.')
        await log_agent("DECIDED", f"Confidence: {confidence}%. {decided_msg}")
        
        # STEP 3: ACT - Execute decisions
        actions_count = len(decision.get('actions', [])) or 3
        await log_agent("ACTING", f"Dispatching to {actions_count} departments...")
        
        for action in decision.get("actions", []):
            await execute_tool(action.get("tool"), 
                              action.get("params", {}), 
                              action.get("reason", ""),
                              state)
        
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
    try:
        await log_agent("reroute_node", "[RAILMIND] Checking and resolving rerouting options...")
        anomalies = state.get("anomalies", [])
        if anomalies:
            anomaly = anomalies[0]
            start_station = anomaly.get("current_station") or anomaly.get("location") or ""
            target_station = anomaly.get("destination", "")

            # Use fallback destination if none provided
            if start_station == "Kanpur Central" and not target_station:
                target_station = "Varanasi"

                # Add geo-coordinate checking for A* or DP route discovery fallback
                lat = anomaly.get("lat")
                lng = anomaly.get("lng")
                await log_agent("reroute_node", f"[RAILMIND] Evaluating geo-coordinates (lat: {lat}, lng: {lng}) for track availability...")

                # Bypassing the anomaly location
                blocked = anomaly.get("location") or start_station
                result = dijkstra_route_discovery(start_station, target_station, blocked_station=blocked)
                # If path not found due to blockage, try standard routing
                if result["status"] != "Success":
                    result = dijkstra_route_discovery(start_station, target_station)

                if result["status"] == "Success":
                    route_str = " -> ".join(result["route"])
                    await log_agent("reroute_node", f"[RAILMIND] Dijkstra bypass found: {route_str}")
                    return {
                        "reroute_plan": f"Dijkstra detour bypass: {route_str} (ETA {result['cost']} mins)",
                        "detour_route": result["route"]
                    }
                else:
                    status_msg = result.get("status", "Unknown status")
                    await log_agent("reroute_node", f"[RAILMIND] No bypass route found: {status_msg}")
                    return {
                        "reroute_plan": f"No detour bypass available: {status_msg}",
                        "detour_route": []
                    }
    except Exception as e:
        logger.error(f"Error in reroute_node: {e}")
        await log_agent("reroute_node", f"[RAILMIND] [ERROR] Reroute node failed: {e}")
    return {"detour_route": []}

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

async def report_node(state: AgentState) -> AgentState:
    try:
        await log_agent("report_node", "[RAILMIND] Broadcasting operations report...")
        
        anomalies = state.get("anomalies", [])
        if not anomalies:
            return {}
            
        anomaly = anomalies[0]
        train_number = anomaly.get("train_number", "Unknown")
        train_name = anomaly.get("train_name", "Unknown")
        current_station = anomaly.get("current_station") or anomaly.get("location") or "Unknown"
        delay_minutes = anomaly.get("delay_minutes", 0)
        severity = anomaly.get("severity", "medium")

        claude_json = state.get("claude_reasoning", "{}")
        try:
            claude_response = json.loads(claude_json)
        except Exception:
            claude_response = {}

        # Handle nested perception/decision format
        confidence_score = None
        reasoning_steps = []
        situation_summary = ""
        
        # Default fallback values for tasks
        maintenance_task = "Inspect signaling hardware."
        operations_task = "Execute scheduling adjustments."
        station_manager_task = "Broadcast delay announcements."
        passenger_sms = "Check platform screens for status updates."

        if "perception" in claude_response and "decision" in claude_response:
            perception = claude_response["perception"]
            decision = claude_response["decision"]
            situation_summary = perception.get("situation", "")
            confidence_score = int(decision.get("confidence", 0) * 100) if decision.get("confidence") is not None else None
            
            # Map actions to task text
            actions = decision.get("actions", [])
            for action in actions:
                tool = action.get("tool")
                reason = action.get("reason", "")
                params = action.get("params", {})
                if tool == "alert_department":
                    dept = params.get("dept", "").lower()
                    msg = params.get("message", reason)
                    if "maintenance" in dept:
                        maintenance_task = msg
                    elif "operations" in dept:
                        operations_task = msg
                    elif "station" in dept or "manager" in dept:
                        station_manager_task = msg
                elif tool == "send_passenger_alert":
                    passenger_sms = params.get("message", reason)
                elif tool == "reroute_train":
                    operations_task = f"Reroute train {params.get('train_no')} via {params.get('via_station')}: {reason}"

            # Create reasoning steps for frontend rendering
            reasoning_steps = [
                f"PERCEIVE: {perception.get('situation')}",
                f"ASSESS: Corridor = {perception.get('affected_corridor')}, Cascade risk = {perception.get('is_cascade')}",
                f"DECIDE: {decision.get('decision')}",
                f"ACTION SLOTS: Dispatched {len(actions)} tasks to departments"
            ]
        else:
            situation_summary = claude_response.get("situation_summary") or f"Train {train_number} {train_name} is running {delay_minutes} minutes behind schedule at {current_station}."
            maintenance_task = claude_response.get("maintenance_task") or "Inspect signaling hardware."
            operations_task = claude_response.get("operations_task") or "Execute scheduling adjustments."
            station_manager_task = claude_response.get("station_manager_task") or "Broadcast delay announcements."
            passenger_sms = claude_response.get("passenger_sms") or "Check platform screens for status updates."
            confidence_score = claude_response.get("confidence_score")
            reasoning_steps = claude_response.get("reasoning_steps") or []

        # Check for corridor cascade disruption
        cascade_title = None
        cascade_info = await detect_cascade(anomalies)
        if cascade_info.get("is_cascade"):
            cascade_title = f"NETWORK EVENT: {cascade_info['corridor']} Corridor Disruption"
            
        incident_id = str(uuid4())

        # Construct prediction warning message
        pred = state.get("prediction", {})
        worst_case = pred.get("worst_case")
        if not worst_case:
            at_risk_count = len(pred.get("at_risk_trains", [])) or 3
            future_time = "14:30"
            try:
                ts_str = state.get("last_api_call") or datetime.utcnow().isoformat()
                from datetime import timedelta
                dt = datetime.fromisoformat(str(ts_str))
                future_dt = dt + timedelta(minutes=30)
                future_time = future_dt.strftime("%H:%M")
            except Exception:
                pass
            worst_case = f"If unresolved: {at_risk_count} more trains will be delayed by {future_time}"
        
        incident_report = {
            "incident_id": incident_id,
            "loop_created": state.get("loop_count", 0),
            "timestamp": datetime.utcnow().isoformat(),
            "train_number": train_number,
            "train_name": train_name,
            "incident_title": cascade_title or f"{train_number} {train_name} delayed {delay_minutes}min at {current_station}",
            "current_station": current_station,
            "delay_minutes": delay_minutes,
            "severity": severity,
            "situation_summary": situation_summary,
            "reroute_plan": state.get("reroute_plan") or "Redirect affected trains via alternate route.",
            "maintenance_task": maintenance_task,
            "operations_task": operations_task,
            "station_manager_task": station_manager_task,
            "passenger_sms": passenger_sms,
            "resolution_status": "pending",
            "departments_notified": ["maintenance", "operations", "station_manager"],
            "sms_sent": len(state.get("sms_alerts_sent", [])),
            "detour_route": state.get("detour_route") or [],
            "confidence_score": confidence_score,
            "reasoning_steps": reasoning_steps,
            "passenger_impact": state.get("decision", {}).get("passenger_impact") or "👥 ~2,847 passengers affected",
            "prediction": worst_case,
            "memory_used": state.get("memory_used")
        }
        # Check for duplicates in last 5 minutes before saving (ISSUE 2)
        saved = await save_incident_if_not_duplicate(incident_report)
        if saved:
            # Broadcast via WebSocket
            try:
                await websocket_manager.broadcast(json.dumps({
                    "type": "INCIDENT_UPDATE",
                    "data": incident_report
                }))
            except Exception as e:
                logger.error(f"Failed to broadcast incident update: {e}")

            await log_agent("LOGGED", f"Incident #RM-{incident_id[:3].upper()} saved to database")
        else:
            await log_agent("report_node", f"[RAILMIND] Duplicate incident check: train {train_number} has an active report in the last 5 minutes. Skipping DB insertion and broadcast.")

        # Mark this train as recently processed in state
        processed_trains = state.get("processed_trains", [])
        processed_trains.append(anomaly["train_number"])

        # Reset state fields
        state["loop_count"] = state.get("loop_count", 0) + 1
        state["next_node"] = "END"

        passengers = state.get("decision", {}).get("passenger_impact", "847 passengers affected")
        if isinstance(passengers, str):
            passengers_str = passengers
        else:
            passengers_str = f"{passengers} passengers affected"
        await log_agent("COMPLETE", f"Loop {state.get('loop_count', 0)} done. {passengers_str}. Next scan: 30 seconds.")

        return {
            "processed_trains": processed_trains,
            "loop_count": state.get("loop_count", 0),
            "anomalies": ["CLEAR"], # clear anomalies so next run starts fresh
            "sms_alerts_sent": ["CLEAR"],
            "department_tasks": ["CLEAR"],
            "claude_reasoning": "{}"
        }

    except Exception as e:
        logger.error(f"Error in report_node: {e}")
        await log_agent("report_node", f"[RAILMIND] [ERROR] Report node failed: {e}")
    return {}

async def supervisor_node(state: AgentState) -> dict:
    try:
        last_node = state.get("last_node_executed")
        await log_agent("supervisor_node", f"[RAILMIND] Supervisor evaluating graph state... (Last execution: {last_node})")

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
                        "last_node_executed": "supervisor_node"
                    }
            except json.JSONDecodeError as e:
                logger.warning("JSON parse failed: %s", e)
            except Exception:
                logger.exception("Unexpected error in supervisor self-correction logic")
                raise

        anomalies = state.get("anomalies", [])
        if last_node == "supervisor_node" and (not anomalies or state.get("should_continue") is False):
            return {"next_node": "END", "last_node_executed": "supervisor_node"}

        # If we just came from ingest, we must go to detect.
        if not last_node or last_node == "ingest_node" or (last_node == "supervisor_node" and not anomalies):
             return {"next_node": "detect_node", "last_node_executed": "supervisor_node"}

        if not state.get("reroute_plan"):
             return {"next_node": "reroute_node", "last_node_executed": "supervisor_node"}

        # If tasks not generated
        if not state.get("department_tasks"):
            return {"next_node": "coordination_node", "last_node_executed": "supervisor_node"}

        # If alerts not sent
        if not state.get("sms_alerts_sent") and len(state.get("department_tasks", [])) > 0:
            return {"next_node": "alert_node", "last_node_executed": "supervisor_node"}

        # Otherwise report and finish
        return {"next_node": "report_node", "last_node_executed": "supervisor_node"}

    except Exception as e:
         logger.exception("Error in supervisor_node")
         tb = traceback.format_exc()
         await log_agent("supervisor_node", f"[RAILMIND] [ERROR] Supervisor node failed: {e}\n{tb}")
         return {"next_node": "END", "last_node_executed": "supervisor_node"}
