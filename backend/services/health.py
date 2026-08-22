"""Real health probes for RailMind subsystems.

Every check in this module performs an actual probe — a network ping, a
credential lookup, a heartbeat age comparison — and reports what it found.
Nothing here returns a hardcoded "Connected". If a subsystem is down, the
dashboard must be able to say so.
"""

import asyncio
import os
import time
from datetime import datetime, timezone

# Component states, ordered worst-to-best for aggregation.
DOWN = "down"
DEGRADED = "degraded"
NOT_CONFIGURED = "not_configured"
OK = "ok"

_SEVERITY = {DOWN: 0, DEGRADED: 1, NOT_CONFIGURED: 2, OK: 3}

# Values that look like a key but aren't one.
_PLACEHOLDERS = {"", "mock_key", "your_key_here", "changeme", "none", "null"}

# How stale the agent heartbeat may get before we stop calling it healthy.
# The background loop sleeps 5s between cycles, so 20s means several missed ticks.
LOOP_DEGRADED_AFTER_S = 20
LOOP_DOWN_AFTER_S = 60


def is_configured(value) -> bool:
    """True if an env value is a real credential rather than a placeholder."""
    return bool(value) and str(value).strip().lower() not in _PLACEHOLDERS


def component(id_, name, status, detail, latency_ms=None):
    return {
        "id": id_,
        "name": name,
        "status": status,
        "detail": detail,
        "latency_ms": latency_ms,
    }


async def check_mongodb(timeout: float = 2.0):
    """Ping MongoDB. Reports the real round-trip time, or why it failed."""
    from .db_client import MONGODB_URI, client, db_client

    if not is_configured(MONGODB_URI) or client is None:
        return component(
            "mongodb", "MongoDB", NOT_CONFIGURED,
            "MONGODB_URI not set — persisting to local JSON fallback file",
        )

    started = time.perf_counter()
    try:
        await asyncio.wait_for(client.admin.command("ping"), timeout=timeout)
        latency = round((time.perf_counter() - started) * 1000)
    except asyncio.TimeoutError:
        return component(
            "mongodb", "MongoDB", DOWN,
            f"No response within {timeout:.0f}s — writes are going to the fallback file",
        )
    except Exception as exc:
        return component(
            "mongodb", "MongoDB", DOWN,
            f"{type(exc).__name__}: {exc}"[:200],
        )

    if db_client.use_fallback:
        return component(
            "mongodb", "MongoDB", DEGRADED,
            "Reachable, but the client latched to fallback after an earlier failure — restart to reattach",
            latency,
        )
    return component("mongodb", "MongoDB", OK, f"Ping {latency} ms", latency)


def check_reasoning_models():
    """Report each LLM provider the pipeline actually calls.

    Two independent paths exist: ai_service.reason_with_ai uses Anthropic,
    and nodes.call_gemini uses Groq (despite its name). Each degrades to a
    hardcoded template when its key is missing, so an unconfigured provider
    means canned text on screen, not an outage.
    """
    checks = []

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    checks.append(component(
        "anthropic", "Mitigation Planner (Anthropic claude-3-5-sonnet)",
        OK if is_configured(anthropic_key) else NOT_CONFIGURED,
        "Key present" if is_configured(anthropic_key)
        else "ANTHROPIC_API_KEY missing — falling back to hardcoded plan templates",
    ))

    groq_key = os.getenv("GROQ_API_KEY")
    checks.append(component(
        "groq", "Perception & Decision (Groq llama3-8b-8192)",
        OK if is_configured(groq_key) else NOT_CONFIGURED,
        "Key present" if is_configured(groq_key)
        else "GROQ_API_KEY missing — perception/decision steps return mock JSON",
    ))

    return checks


def check_railways_api(agent_state: dict):
    """Report where train positions are actually coming from.

    Key presence is not evidence of a working feed: every upstream provider in
    railways_api.py degrades silently into a mock generator that returns data
    in the identical shape. This reads the recorded outcome of recent lookups
    so a fully-simulated feed cannot present itself as live telemetry.
    """
    from .railways_api import RAILWAYS_API_KEY, feed_summary

    name = "Railway Telemetry Feed"
    configured = is_configured(RAILWAYS_API_KEY) or is_configured(os.getenv("RAPIDAPI_KEY"))
    summary = feed_summary()
    attempts, live = summary["attempts"], summary["live"]
    latency = agent_state.get("railways_latency_ms") or None

    if attempts == 0:
        if not configured:
            return component(
                "railways_api", name, NOT_CONFIGURED,
                "No RAILWAYS_API_KEY/RAPIDAPI_KEY set — lookups will return simulated positions",
            )
        return component("railways_api", name, DEGRADED, "No train lookup has run yet this session")

    sources = ", ".join(f"{k}×{v}" for k, v in sorted(summary["sources"].items()))
    detail = f"{live}/{attempts} recent lookups returned live data ({sources})"
    err = summary["last_error"]

    if live == 0:
        return component(
            "railways_api", name, DOWN,
            f"Every one of the last {attempts} lookups fell back to simulated positions"
            + (f" — last upstream error: {err}" if err else ""),
        )
    if live < attempts:
        return component("railways_api", name, DEGRADED, detail, latency)
    return component("railways_api", name, OK, detail, latency)


def check_twilio():
    """Report whether an SMS would actually leave the building."""
    from .twilio_service import client as twilio_client

    if os.getenv("DEMO_MODE") == "true":
        return component(
            "twilio", "SMS Dispatch (Twilio)", DEGRADED,
            "DEMO_MODE=true — alerts are logged to console, no SMS is sent",
        )
    if twilio_client is None:
        return component(
            "twilio", "SMS Dispatch (Twilio)", NOT_CONFIGURED,
            "TWILIO_ACCOUNT_SID/AUTH_TOKEN missing — department alerts are skipped",
        )
    if not is_configured(os.getenv("TWILIO_PHONE_NUMBER")):
        return component(
            "twilio", "SMS Dispatch (Twilio)", DEGRADED,
            "Client authenticated but TWILIO_PHONE_NUMBER is unset — sends will fail",
        )
    return component("twilio", "SMS Dispatch (Twilio)", OK, "Client authenticated, sender configured")


def check_agent_loop(agent_state: dict):
    """Compare the orchestrator's last heartbeat against wall-clock time."""
    last_tick = agent_state.get("last_loop_at")
    loop_count = agent_state.get("loop_count", 0)
    last_error = agent_state.get("last_loop_error")

    if not last_tick:
        return component(
            "agent_loop", "Agent Orchestrator", DEGRADED,
            "No cycle has completed yet since startup",
        )

    try:
        ticked = datetime.fromisoformat(last_tick)
        if ticked.tzinfo is None:
            ticked = ticked.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - ticked).total_seconds()
    except Exception:
        return component(
            "agent_loop", "Agent Orchestrator", DEGRADED,
            f"Unreadable heartbeat timestamp: {last_tick}",
        )

    detail = f"Cycle #{loop_count}, {age:.0f}s ago"
    if last_error:
        detail += f" — last error: {str(last_error)[:120]}"

    if age > LOOP_DOWN_AFTER_S:
        return component("agent_loop", "Agent Orchestrator", DOWN, f"Stalled — {detail}")
    if age > LOOP_DEGRADED_AFTER_S or last_error:
        return component("agent_loop", "Agent Orchestrator", DEGRADED, detail)
    return component("agent_loop", "Agent Orchestrator", OK, detail)


async def collect_system_status(agent_state: dict):
    """Run every probe and return a single status document."""
    mongo = await check_mongodb()

    components = [
        check_agent_loop(agent_state),
        check_railways_api(agent_state),
        *check_reasoning_models(),
        mongo,
        check_twilio(),
    ]

    worst = min((_SEVERITY[c["status"]] for c in components), default=_SEVERITY[OK])
    if worst <= _SEVERITY[DOWN]:
        overall = DOWN
    elif worst <= _SEVERITY[DEGRADED]:
        overall = DEGRADED
    else:
        overall = OK

    return {
        "overall": overall,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "components": components,
        "contacts": {
            "maintenance": os.getenv("MAINTENANCE_PHONE") or None,
            "operations": os.getenv("OPERATIONS_PHONE") or None,
            "station_manager": os.getenv("STATION_PHONE") or None,
        },
    }
