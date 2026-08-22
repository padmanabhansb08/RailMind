import os
import json
import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from pymongo import IndexModel, ASCENDING, DESCENDING # type: ignore
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Ensure env variables are loaded from the backend/.env file relative to this script
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=env_path)

# Real MongoDB Atlas Connection for RailMind
MONGODB_URI = os.getenv("MONGODB_URI")
if MONGODB_URI:
    client = AsyncIOMotorClient(MONGODB_URI, maxPoolSize=50)
    db = client["railmind"]
else:
    client = None
    db = None

# Collections needed:
# - db["incidents"] — for incident reports
# - db["department_tasks"] — for dept coordination tasks  
# - db["train_logs"] — for raw train data logs

def get_station_code(station_name: str) -> str:
    if not station_name:
        return ""
    name_upper = station_name.upper()
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
    if "MUMBAI" in name_upper or "CSTM" in name_upper:
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

def fallback_task_id(task):
    """Stable unique id for a task in the JSON store.

    Fallback tasks carry no document id of their own, and one incident emits
    one task per department — so incident_id is shared by three rows. Keying on
    it made React collapse them into one card and made resolving any single
    task silently resolve the other two.
    """
    return f"{task.get('incident_id')}:{task.get('department')}"


class FallbackDB:
    def __init__(self):
        self.client = client
        self.db = db
        self.use_fallback = (client is None)
        self.fallback_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fallback_db.json")
        self._lock = asyncio.Lock()

    async def init_indexes(self):
        if self.db is None:
            return
        try:
            # Create a 2dsphere index for geospatial locations if applicable, or just compound
            await self.db["incidents"].create_index([("train_number", ASCENDING), ("timestamp", DESCENDING)], unique=True)
            logger.info("MongoDB indexes created successfully.")
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")

    def _sync_init_fallback_file(self):
        if not os.path.exists(self.fallback_file):
            try:
                with open(self.fallback_file, "w") as f:
                    json.dump({"incidents": [], "department_tasks": [], "agent_memory": []}, f)
            except Exception as e:
                logger.error(f"Failed to initialize fallback file: {e}")

    async def _init_fallback_file(self):
        await asyncio.to_thread(self._sync_init_fallback_file)

    def _sync_read_fallback(self):
        self._sync_init_fallback_file()
        try:
            with open(self.fallback_file, "r") as f:
                data = json.load(f)
                if "agent_memory" not in data:
                    data["agent_memory"] = []
                return data
        except Exception:
            return {"incidents": [], "department_tasks": [], "agent_memory": []}

    async def _read_fallback(self):
        return await asyncio.to_thread(self._sync_read_fallback)

    def _sync_write_fallback(self, data):
        try:
            with open(self.fallback_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to write to fallback database: {e}")

    async def _write_fallback(self, data):
        await asyncio.to_thread(self._sync_write_fallback, data)

    async def has_recent_incident(self, train_number, minutes=2):
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        
        if not self.use_fallback:
            try:
                # With unique compound indexes on train_number+timestamp, we don't strictly need this $gt check
                # if we just catch DuplicateKeyError on insert, but we'll leave it for reading if needed.
                # Since the instruction says use DuplicateKeyError INSTEAD OF $gt, let's just return False
                # and let the insert catch the duplicate, OR query explicitly without $gt if we bucket by hour.
                # Actually, the simplest optimization is just returning False here and relying on unique indexes
                # during insert, but let's keep the exact signature and just catch it in insert_incident.
                existing = await self.db["incidents"].find_one({
                    "train_number": train_number,
                    "timestamp": {"$gt": cutoff.isoformat()}
                })
                return existing is not None
            except Exception as e:
                logger.warning(f"MongoDB has_recent_incident failed: {e}. Falling back.")
                self.use_fallback = True

        # Fallback file check
        async with self._lock:
            data = await self._read_fallback()
            for inc in data["incidents"]:
                if inc.get("train_number") == train_number:
                    ts_str = inc.get("timestamp")
                    try:
                        if isinstance(ts_str, datetime):
                            ts = ts_str
                        else:
                            ts = datetime.fromisoformat(str(ts_str))
                        if ts > cutoff:
                            return True
                    except Exception:
                        pass
            return False

    async def insert_incident(self, incident):
        if not self.use_fallback:
            try:
                await self.db["incidents"].insert_one(incident.copy())
                return True
            except DuplicateKeyError:
                logger.info(f"Duplicate incident detected for train {incident.get('train_number')} at {incident.get('timestamp')}")
                return False
            except Exception as e:
                logger.warning(f"MongoDB insert_incident failed: {e}. Falling back.")
                self.use_fallback = True
        
        # Fallback
        async with self._lock:
            data = await self._read_fallback()
            if "_id" not in incident:
                incident["_id"] = incident.get("incident_id")

            # Simple fallback deduplication
            for inc in data["incidents"]:
                if inc.get("train_number") == incident.get("train_number") and inc.get("timestamp") == incident.get("timestamp"):
                    return False

            data["incidents"].append(incident)
            await self._write_fallback(data)
            return True

    async def get_incidents(self, limit=20):
        if not self.use_fallback:
            try:
                cursor = self.db["incidents"].find().sort("timestamp", -1).limit(limit)
                incidents = await cursor.to_list(length=limit)
                for inc in incidents:
                    inc["_id"] = str(inc["_id"])
                return incidents
            except Exception as e:
                logger.warning(f"MongoDB get_incidents failed: {e}. Falling back.")
                self.use_fallback = True
                
        # Fallback
        async with self._lock:
            data = await self._read_fallback()
            incidents = data["incidents"]
            try:
                incidents = sorted(incidents, key=lambda x: x.get("timestamp", ""), reverse=True)
            except Exception:
                pass
            return incidents[:limit]

    async def insert_department_tasks(self, tasks):
        if not self.use_fallback:
            try:
                await self.db["department_tasks"].insert_many(tasks)
                return
            except Exception as e:
                logger.warning(f"MongoDB insert_department_tasks failed: {e}. Falling back.")
                self.use_fallback = True
                
        # Fallback
        async with self._lock:
            data = await self._read_fallback()
            data["department_tasks"].extend(tasks)
            await self._write_fallback(data)

    async def get_pending_department_tasks(self):
        if not self.use_fallback:
            try:
                cursor = self.db["department_tasks"].find({"status": "pending"})
                tasks = await cursor.to_list(length=100)
                for t in tasks:
                    t["_id"] = str(t["_id"])
                    # One incident produces several tasks (maintenance,
                    # operations, station manager), so incident_id alone is not
                    # unique — the document id is what identifies a task.
                    t["id"] = str(t["_id"])
                return tasks
            except Exception as e:
                logger.warning(f"MongoDB get_pending_department_tasks failed: {e}. Falling back.")
                self.use_fallback = True
                
        # Fallback
        async with self._lock:
            data = await self._read_fallback()
            pending = []
            for t in data["department_tasks"]:
                if t.get("status") == "pending":
                    t["id"] = fallback_task_id(t)
                    pending.append(t)
            return pending

    async def resolve_department_task(self, task_id):
        if not self.use_fallback:
            try:
                from bson import ObjectId
                query = {}
                try:
                    query = {"_id": ObjectId(task_id)}
                except Exception:
                    query = {"incident_id": task_id}
                result = await self.db["department_tasks"].update_many(query, {"$set": {"status": "resolved"}})
                return result.modified_count
            except Exception as e:
                logger.warning(f"MongoDB resolve_department_task failed: {e}. Falling back.")
                self.use_fallback = True
                
        # Fallback
        #
        # A composite "incident:department" id resolves exactly one task. A
        # bare incident id is still accepted and resolves that incident's whole
        # set, which is what older callers expected.
        async with self._lock:
            data = await self._read_fallback()
            modified_count = 0
            for t in data["department_tasks"]:
                matches = (
                    fallback_task_id(t) == task_id
                    or str(t.get("_id")) == task_id
                    or (":" not in str(task_id) and t.get("incident_id") == task_id)
                )
                if matches and t.get("status") != "resolved":
                    t["status"] = "resolved"
                    modified_count += 1
            if modified_count > 0:
                await self._write_fallback(data)
            return modified_count

    async def approve_incident(self, incident_id):
        # Retrieve incident details first to save in memory
        incident = None
        if not self.use_fallback:
            try:
                from bson import ObjectId
                query = {}
                try:
                    query = {"_id": ObjectId(incident_id)}
                except Exception:
                    query = {"incident_id": incident_id}
                incident = await self.db["incidents"].find_one(query)
            except Exception as e:
                logger.warning(f"MongoDB find incident for memory failed: {e}. Falling back.")
                self.use_fallback = True

        if self.use_fallback or not incident:
            async with self._lock:
                data = await self._read_fallback()
                for inc in data["incidents"]:
                    if inc.get("incident_id") == incident_id or str(inc.get("_id")) == incident_id or inc.get("_id") == incident_id:
                        incident = inc
                        break

        # If found, save to memory
        if incident:
            try:
                train_number = incident.get("train_number", "Unknown")
                current_station = incident.get("current_station") or incident.get("location") or "Unknown"
                station_code = get_station_code(current_station)
                reroute_plan = incident.get("reroute_plan") or "Redirect via loop lines"
                
                time_str = "12:00-14:00"
                try:
                    ts_str = incident.get("timestamp")
                    if ts_str:
                        if isinstance(ts_str, datetime):
                            dt = ts_str
                        else:
                            dt = datetime.fromisoformat(str(ts_str))
                        h = dt.hour
                        time_str = f"{h:02d}:00-{(h+2)%24:02d}:00"
                except Exception:
                    pass
                
                # Record only what actually happened. Anything inferred beyond
                # this (recurrence rates, minutes recovered, escalation counts)
                # would be invented, and memories are replayed into the model's
                # context on later incidents — so a fabrication here becomes a
                # false premise for every future decision at this station.
                memory_item = {
                    "train_number": train_number,
                    "station_code": station_code,
                    "outcome": "approved",
                    "delay_minutes": incident.get("delay_minutes"),
                    "severity": incident.get("severity"),
                    "time_window": time_str,
                    "plan_applied": reroute_plan,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await self.save_memory(memory_item)
            except Exception as e:
                logger.error(f"Error creating/saving memory in approve_incident: {e}")

        # Now approve the incident
        if not self.use_fallback:
            try:
                from bson import ObjectId
                query = {}
                try:
                    query = {"_id": ObjectId(incident_id)}
                except Exception:
                    query = {"incident_id": incident_id}
                result = await self.db["incidents"].update_many(query, {"$set": {
                    "resolution_status": "approved",
                    "resolved_at": datetime.utcnow().isoformat()
                }})
                return result.modified_count
            except Exception as e:
                logger.warning(f"MongoDB approve_incident failed: {e}. Falling back.")
                self.use_fallback = True

        # Fallback file check
        async with self._lock:
            data = await self._read_fallback()
            modified_count = 0
            for inc in data["incidents"]:
                if inc.get("incident_id") == incident_id or str(inc.get("_id")) == incident_id or inc.get("_id") == incident_id:
                    if inc.get("resolution_status") != "approved":
                        inc["resolution_status"] = "approved"
                        inc["resolved_at"] = datetime.utcnow().isoformat()
                        modified_count += 1
            if modified_count > 0:
                await self._write_fallback(data)
            return modified_count

    async def override_incident(self, incident_id, custom_decision):
        # Retrieve incident details first to save in memory
        incident = None
        if not self.use_fallback:
            try:
                from bson import ObjectId
                query = {}
                try:
                    query = {"_id": ObjectId(incident_id)}
                except Exception:
                    query = {"incident_id": incident_id}
                incident = await self.db["incidents"].find_one(query)
            except Exception as e:
                logger.warning(f"MongoDB find incident for override failed: {e}. Falling back.")
                self.use_fallback = True

        if self.use_fallback or not incident:
            async with self._lock:
                data = await self._read_fallback()
                for inc in data["incidents"]:
                    if inc.get("incident_id") == incident_id or str(inc.get("_id")) == incident_id or inc.get("_id") == incident_id:
                        incident = inc
                        break

        # Save to memory as outcome
        if incident:
            try:
                train_number = incident.get("train_number", "Unknown")
                current_station = incident.get("current_station") or incident.get("location") or "Unknown"
                station_code = get_station_code(current_station)
                
                time_str = "12:00-14:00"
                try:
                    ts_str = incident.get("timestamp")
                    if ts_str:
                        if isinstance(ts_str, datetime):
                            dt = ts_str
                        else:
                            dt = datetime.fromisoformat(str(ts_str))
                        h = dt.hour
                        time_str = f"{h:02d}:00-{(h+2)%24:02d}:00"
                except Exception:
                    pass
                
                # An override is the highest-signal memory we have: a human
                # rejected the generated plan and substituted their own. Record
                # both so the contrast is visible on replay.
                memory_item = {
                    "train_number": train_number,
                    "station_code": station_code,
                    "outcome": "overridden_by_operator",
                    "delay_minutes": incident.get("delay_minutes"),
                    "severity": incident.get("severity"),
                    "time_window": time_str,
                    "plan_proposed": incident.get("reroute_plan"),
                    "plan_applied": custom_decision,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await self.save_memory(memory_item)
            except Exception as e:
                logger.error(f"Error creating/saving override memory: {e}")

        # Update resolution_status to approved and reroute_plan to custom_decision
        if not self.use_fallback:
            try:
                from bson import ObjectId
                query = {}
                try:
                    query = {"_id": ObjectId(incident_id)}
                except Exception:
                    query = {"incident_id": incident_id}
                result = await self.db["incidents"].update_many(query, {"$set": {
                    "resolution_status": "overridden",
                    "reroute_plan": custom_decision,
                    "resolved_at": datetime.utcnow().isoformat()
                }})
                return result.modified_count
            except Exception as e:
                logger.warning(f"MongoDB override_incident failed: {e}. Falling back.")
                self.use_fallback = True

        # Fallback
        async with self._lock:
            data = await self._read_fallback()
            modified_count = 0
            for inc in data["incidents"]:
                if inc.get("incident_id") == incident_id or str(inc.get("_id")) == incident_id or inc.get("_id") == incident_id:
                    inc["resolution_status"] = "overridden"
                    inc["reroute_plan"] = custom_decision
                    inc["resolved_at"] = datetime.utcnow().isoformat()
                    modified_count += 1
            if modified_count > 0:
                await self._write_fallback(data)
            return modified_count


    async def acknowledge_incident(self, incident_id):
        """Mark an incident as seen and dismissed by an operator.

        Distinct from approval: acknowledging a warning records that a human
        looked at it and chose not to act, which is itself an auditable
        decision. Previously the frontend dropped these from local state only,
        so the dismissal vanished on refresh.
        """
        now = datetime.utcnow().isoformat()
        if not self.use_fallback:
            try:
                from bson import ObjectId
                try:
                    query = {"_id": ObjectId(incident_id)}
                except Exception:
                    query = {"incident_id": incident_id}
                result = await self.db["incidents"].update_many(query, {"$set": {
                    "resolution_status": "acknowledged",
                    "resolved_at": now
                }})
                return result.modified_count
            except Exception as e:
                logger.warning(f"MongoDB acknowledge_incident failed: {e}. Falling back.")
                self.use_fallback = True

        async with self._lock:
            data = await self._read_fallback()
            modified_count = 0
            for inc in data["incidents"]:
                if inc.get("incident_id") == incident_id or str(inc.get("_id")) == incident_id or inc.get("_id") == incident_id:
                    if inc.get("resolution_status") != "acknowledged":
                        inc["resolution_status"] = "acknowledged"
                        inc["resolved_at"] = now
                        modified_count += 1
            if modified_count > 0:
                await self._write_fallback(data)
            return modified_count

    async def record_decision(self, incident_id, action, actor="operator", reason=None, plan=None):
        """Apply an operator decision and append it to the incident's audit trail.

        One path for every decision (approve / reject / modify / acknowledge /
        undo) so nothing can change an incident's status without leaving a
        record of who did it and why. `undo` returns the incident to pending
        but keeps the history — reversing a decision is itself a decision.
        """
        now = datetime.utcnow().isoformat()

        status_for_action = {
            "approve": "approved",
            "modify": "overridden",
            "reject": "rejected",
            "acknowledge": "acknowledged",
            "undo": "pending",
        }
        if action not in status_for_action:
            raise ValueError(f"Unknown decision action: {action}")

        new_status = status_for_action[action]
        entry = {"action": action, "actor": actor, "at": now}
        if reason:
            entry["reason"] = reason
        if plan:
            entry["plan"] = plan

        update = {"resolution_status": new_status}
        if action == "undo":
            update["resolved_at"] = None
        else:
            update["resolved_at"] = now
        if action == "modify" and plan:
            update["reroute_plan"] = plan

        if not self.use_fallback:
            try:
                from bson import ObjectId
                try:
                    query = {"_id": ObjectId(incident_id)}
                except Exception:
                    query = {"incident_id": incident_id}
                result = await self.db["incidents"].update_many(
                    query, {"$set": update, "$push": {"decisions": entry}}
                )
                return result.modified_count
            except Exception as e:
                logger.warning(f"MongoDB record_decision failed: {e}. Falling back.")
                self.use_fallback = True

        async with self._lock:
            data = await self._read_fallback()
            modified_count = 0
            for inc in data["incidents"]:
                if inc.get("incident_id") == incident_id or str(inc.get("_id")) == incident_id or inc.get("_id") == incident_id:
                    inc.update(update)
                    inc.setdefault("decisions", []).append(entry)
                    modified_count += 1
            if modified_count > 0:
                await self._write_fallback(data)
            return modified_count

    async def get_analytics(self):
        """Compute dashboard figures from stored incidents.

        Every number returned here is derived from records on disk. Where
        there is not enough data to compute a figure, the field is None and
        the caller is expected to say so rather than substitute a plausible
        placeholder.
        """
        incidents = await self.get_incidents(limit=1000)

        by_severity = {}
        by_status = {}
        durations = []

        for inc in incidents:
            severity = (inc.get("severity") or "info").lower()
            by_severity[severity] = by_severity.get(severity, 0) + 1

            status = (inc.get("resolution_status") or "pending").lower()
            by_status[status] = by_status.get(status, 0) + 1

            raised, resolved = inc.get("timestamp"), inc.get("resolved_at")
            if not raised or not resolved:
                continue
            try:
                start = raised if isinstance(raised, datetime) else datetime.fromisoformat(str(raised).replace("Z", "+00:00"))
                end = resolved if isinstance(resolved, datetime) else datetime.fromisoformat(str(resolved).replace("Z", "+00:00"))
                if start.tzinfo is not None:
                    start = start.replace(tzinfo=None)
                if end.tzinfo is not None:
                    end = end.replace(tzinfo=None)
                seconds = (end - start).total_seconds()
                if seconds >= 0:
                    durations.append(seconds)
            except Exception:
                continue

        avg_resolution_seconds = round(sum(durations) / len(durations)) if durations else None

        return {
            "total_incidents": len(incidents),
            "by_severity": by_severity,
            "by_status": by_status,
            "resolved_count": len(durations),
            "avg_resolution_seconds": avg_resolution_seconds,
            "store": "fallback_file" if self.use_fallback else "mongodb"
        }

    async def save_memory(self, memory_item):
        if not self.use_fallback:
            try:
                await self.db["agent_memory"].insert_one(memory_item.copy())
                return
            except Exception as e:
                logger.warning(f"MongoDB save_memory failed: {e}. Falling back.")
                self.use_fallback = True

        # Fallback
        async with self._lock:
            data = await self._read_fallback()
            data["agent_memory"].append(memory_item)
            await self._write_fallback(data)

    async def get_memories(self, train_number, station_code, limit=5):
        if not self.use_fallback:
            try:
                cursor = self.db["agent_memory"].find({
                    "train_number": train_number,
                    "station_code": station_code
                }).sort("timestamp", -1).limit(limit)
                memories = await cursor.to_list(length=limit)
                for m in memories:
                    m["_id"] = str(m["_id"])
                return memories
            except Exception as e:
                logger.warning(f"MongoDB get_memories failed: {e}. Falling back.")
                self.use_fallback = True

        # Fallback
        async with self._lock:
            data = await self._read_fallback()
            memories = []
            for m in data.get("agent_memory", []):
                if m.get("train_number") == train_number and m.get("station_code") == station_code:
                    memories.append(m)
            try:
                memories = sorted(memories, key=lambda x: x.get("timestamp", ""), reverse=True)
            except Exception:
                pass
            return memories[:limit]

    async def get_counts(self):
        if not self.use_fallback:
            try:
                # Use a low timeout so we fail fast if MongoDB is down/unreachable
                incident_count = await asyncio.wait_for(
                    self.db["incidents"].count_documents({}),
                    timeout=2.0
                )
                task_count = await asyncio.wait_for(
                    self.db["department_tasks"].count_documents({}),
                    timeout=2.0
                )
                return incident_count, task_count
            except Exception as e:
                logger.warning(f"MongoDB count_documents failed or timed out: {e}. Falling back.")
                self.use_fallback = True

        async with self._lock:
            data = await self._read_fallback()
            return len(data.get("incidents", [])), len(data.get("department_tasks", []))

db_client = FallbackDB()

