"""RailRadar client: full route geometry and real-time running status.

Two endpoints carry complementary halves of the picture and neither is
sufficient alone:

  GET /v1/trains/{no}        static  — every stop with lat/lng (97 for 19310)
  GET /v1/trains/{no}/live   live    — per-stop status, times, platform,
                                       current position, delay, exceptions,
                                       but no coordinates at all

Joining them on the stop `sequence` yields a route that is both fully
positioned and current, which is what the map and the detail view need. The
live-map endpoint used elsewhere reports only the current and next station,
which is why routes previously rendered as two-point stubs.

Anything this module cannot obtain is returned as None. No coordinate, delay
or status is ever interpolated to fill a gap.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=env_path)

BASE_URL = "https://api.railradar.in/v1"
IST = timezone(timedelta(hours=5, minutes=30))
TIMEOUT_SECONDS = 20

# Cached separately: the route is timetable data that changes rarely, while
# running status is only useful while fresh.
STATIC_TTL_SECONDS = 6 * 60 * 60
LIVE_TTL_SECONDS = 60

_static_cache = {}
_live_cache = {}


class TrainNotFound(Exception):
    """RailRadar has no such train number."""


class RailRadarUnavailable(Exception):
    """RailRadar could not be reached or refused the request."""


_api_keys = []
_current_key_idx = 0

def get_api_keys():
    global _api_keys
    if not _api_keys:
        keys_str = os.getenv("RAILRADAR_API_KEYS", "")
        if keys_str:
            _api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        else:
            single_key = os.getenv("RAILRADAR_API_KEY")
            if single_key:
                _api_keys = [single_key.strip()]
    return _api_keys

def api_key():
    keys = get_api_keys()
    if not keys:
        return None
    global _current_key_idx
    return keys[_current_key_idx % len(keys)]

def rotate_api_key():
    global _current_key_idx
    _current_key_idx += 1
    
def is_configured():
    keys = get_api_keys()
    return bool(keys) and any(k.strip().lower() not in {"", "your_key_here", "mock_key"} for k in keys)


def today_ist():
    return datetime.now(IST).strftime("%Y-%m-%d")


async def _get(path, params=None):
    if not is_configured():
        raise RailRadarUnavailable("RAILRADAR_API_KEYS is not configured.")

    url = f"{BASE_URL}{path}"
    
    keys = get_api_keys()
    for attempt in range(len(keys)):
        current_key = api_key()
        headers = {"Authorization": f"Bearer {current_key}"}
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.get(url, headers=headers, params=params)
        except Exception as exc:
            raise RailRadarUnavailable(f"{type(exc).__name__}: {exc}") from exc

        if response.status_code in {429, 401, 403}:
            rotate_api_key()
            if attempt < len(keys) - 1:
                continue # try next key
            if response.status_code == 429:
                raise RailRadarUnavailable("RailRadar rate limit reached on all keys.")
            raise RailRadarUnavailable("RailRadar rejected the API keys.")

        if response.status_code == 404:
            raise TrainNotFound(f"RailRadar has no record for this train.")
        if response.status_code != 200:
            raise RailRadarUnavailable(f"RailRadar returned HTTP {response.status_code}.")

        payload = response.json()
        if not payload.get("success"):
            error = (payload.get("error") or {})
            if error.get("code") == "TRAIN_NOT_FOUND":
                raise TrainNotFound(error.get("message", "Train not found"))
            raise RailRadarUnavailable(error.get("message", "RailRadar request failed."))
        return payload.get("data") or {}
        
    raise RailRadarUnavailable("RailRadar API request failed.")


def _cached(store, key, ttl):
    entry = store.get(key)
    if not entry:
        return None
    if (datetime.now(timezone.utc) - entry["at"]).total_seconds() > ttl:
        return None
    return entry["data"]


def _store(store, key, data):
    store[key] = {"at": datetime.now(timezone.utc), "data": data}


async def fetch_static(train_number):
    """Timetable and full route geometry."""
    cached = _cached(_static_cache, train_number, STATIC_TTL_SECONDS)
    if cached is not None:
        return cached
    data = await _get(f"/trains/{train_number}")
    _store(_static_cache, train_number, data)
    return data


async def fetch_live(train_number, journey_date=None):
    """Current running status for a given journey date."""
    journey_date = journey_date or today_ist()
    key = f"{train_number}:{journey_date}"
    cached = _cached(_live_cache, key, LIVE_TTL_SECONDS)
    if cached is not None:
        return cached
    data = await _get(f"/trains/{train_number}/live", params={"journeyDate": journey_date})
    _store(_live_cache, key, data)
    return data


def build_route(static_data, live_data):
    """Merge coordinates from the static route into the live route.

    Keyed on `sequence`, which both endpoints agree on; station code is a
    fallback because a route can visit the same code twice. Stops the live
    feed omits are still returned, marked with a null status, so the drawn
    line stays geometrically complete.
    """
    static_route = (static_data or {}).get("route") or []
    live_route = (live_data or {}).get("route") or []

    coords_by_seq, coords_by_code = {}, {}
    for stop in static_route:
        station = stop.get("station") or {}
        point = {
            "lat": station.get("lat"),
            "lng": station.get("lng"),
            "name": station.get("name"),
            "code": station.get("code"),
            "distance": stop.get("distance"),
            "is_halt": stop.get("isHalt"),
        }
        if stop.get("sequence") is not None:
            coords_by_seq[stop["sequence"]] = point
        if station.get("code"):
            coords_by_code.setdefault(station["code"], point)

    source = live_route or static_route
    merged = []
    for stop in source:
        if live_route:
            seq = stop.get("sequence")
            code = stop.get("stationCode")
            point = coords_by_seq.get(seq) or coords_by_code.get(code) or {}
            merged.append({
                "sequence": seq,
                "code": code,
                "name": stop.get("stationName") or point.get("name"),
                "lat": point.get("lat"),
                "lng": point.get("lng"),
                "is_halt": stop.get("isHalt"),
                "status": stop.get("status"),
                "platform": stop.get("platform"),
                "distance": stop.get("distance"),
                "scheduled_arrival": stop.get("scheduledArrival"),
                "scheduled_departure": stop.get("scheduledDeparture"),
                "actual_arrival": stop.get("actualArrival"),
                "actual_departure": stop.get("actualDeparture"),
                "delay_minutes": stop.get("delayMinutes"),
                "speed_to_next_kmph": stop.get("speedToNextStationKmph"),
            })
        else:
            station = stop.get("station") or {}
            merged.append({
                "sequence": stop.get("sequence"),
                "code": station.get("code"),
                "name": station.get("name"),
                "lat": station.get("lat"),
                "lng": station.get("lng"),
                "is_halt": stop.get("isHalt"),
                "status": None,
                "platform": None,
                "distance": stop.get("distance"),
                "scheduled_departure": stop.get("departure"),
                "speed_to_next_kmph": stop.get("speedToNextStationKmph"),
            })
    return merged


def locate(live_data, route):
    """Resolve the train's position to coordinates from its route.

    RailRadar reports position as a stop sequence, not a lat/lng, so the
    coordinates come from that stop. `is_actual_position` passes through
    untouched: when RailRadar says the fix is inferred rather than observed,
    that qualification must survive to the operator.
    """
    current = (live_data or {}).get("currentLocation") or {}
    seq = current.get("sequence")

    stop = next((s for s in route if s.get("sequence") == seq), None)
    if stop is None and current.get("stationCode"):
        stop = next((s for s in route if s.get("code") == current["stationCode"]), None)

    return {
        "station_code": current.get("stationCode"),
        "station_name": current.get("stationName") or (stop or {}).get("name"),
        "sequence": seq,
        "status": current.get("status"),
        "is_halt": current.get("isHalt"),
        "is_actual_position": current.get("isActualPosition"),
        "lat": (stop or {}).get("lat"),
        "lng": (stop or {}).get("lng"),
        "delay_minutes": current.get("delayMinutes"),
    }


async def get_train(train_number, journey_date=None):
    """Full picture for one train: timetable, route geometry, live status.

    The static half is required. The live half is optional — a train that is
    not currently running still has a real route worth showing — so a live
    failure degrades to `is_live: False` with the reason attached, rather than
    failing the whole lookup.
    """
    static_data = await fetch_static(train_number)

    live_data, live_error = None, None
    try:
        live_data = await fetch_live(train_number, journey_date)
    except TrainNotFound:
        live_error = "No journey found for this date."
    except RailRadarUnavailable as exc:
        live_error = str(exc)
    except Exception as exc:
        live_error = f"{type(exc).__name__}: {exc}"

    route = build_route(static_data, live_data)
    train = (static_data or {}).get("train") or {}
    position = locate(live_data, route) if live_data else None

    return {
        "train_number": str(train.get("number") or train_number),
        "train_name": train.get("name"),
        "type": train.get("type"),
        "category": train.get("category"),
        "source": train.get("source"),
        "destination": train.get("destination"),
        "run_days": train.get("runDays"),
        "distance_km": train.get("distance"),
        "duration": train.get("duration"),
        "avg_speed_kmph": train.get("avgSpeed"),
        "max_speed_kmph": train.get("maxSpeed"),
        "total_halts": train.get("totalHalts"),

        "journey_date": (live_data or {}).get("startDate") or journey_date,
        "is_live": bool(live_data and live_data.get("isLive")),
        "tracking_mode": (live_data or {}).get("trackingMode"),
        "run_status": (live_data or {}).get("status"),
        "delay_minutes": (live_data or {}).get("delayMinutes"),
        "last_updated_at": (live_data or {}).get("lastUpdatedAt"),
        "live_error": live_error,

        "position": position,
        "previous_halt": (live_data or {}).get("previousHalt"),
        "next_halt": (live_data or {}).get("nextHalt"),
        "exceptions": (live_data or {}).get("exceptions") or [],

        "route": route,
        "route_stop_count": len(route),
        "route_has_coordinates": sum(1 for s in route if s.get("lat") is not None),
    }
