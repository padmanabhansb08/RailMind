"""Turns one detected anomaly into a response plan written about that anomaly.

Why this exists: the reasoning path used to fall back to a fixed block of text
about train 12301 rerouting via Allahabad, no matter which train had actually
been detected. An operator injecting a 95-minute delay on 12951 at Kota Junction
got back a plan naming a different train at a different station, with a fixed
"0.94 confidence" and an invented passenger count attached. That is worse than
no plan: it looks authoritative and describes something that is not happening.

Everything below is derived from fields the pipeline actually recorded on the
anomaly — train, station, delay, status, route, and the other anomalies seen in
the same cycle. Where a number is not measured it is not stated. There is no
passenger count here, because nothing in the feed counts passengers.

This is the deterministic floor. When a reasoning model is reachable its output
is used instead; when it is not, the operator still gets specific, actionable
text rather than a template about someone else's train.
"""

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def severity_for_delay(delay_minutes):
    """The same thresholds detect_node uses, kept in one place."""
    if delay_minutes > 120:
        return "critical"
    if delay_minutes > 60:
        return "high"
    if delay_minutes > 30:
        return "medium"
    if delay_minutes > 15:
        return "low"
    return "info"


def _int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _clean(value, fallback):
    text = str(value or "").strip()
    return text if text and text.lower() not in ("unknown", "none", "-") else fallback


def recovery_estimate(delay_minutes):
    """How long the delay itself implies, stated as a bound rather than a promise.

    Recovery depends on pathing and crew relief, neither of which this system
    can see, so the wording never claims the train will be on time by a
    particular clock reading.
    """
    if delay_minutes <= 0:
        return None
    if delay_minutes <= 30:
        return "Recoverable within the run if a clear path is granted at the next section."
    if delay_minutes <= 90:
        return "Unlikely to recover within this run without priority pathing; expect the delay to carry to the destination."
    return "Will not recover within this run. Downstream connections and the return working need re-planning."


def build_plan(anomaly, peers=None, now=None):
    """A response plan for one anomaly, written about that anomaly.

    `peers` are the other anomalies detected in the same cycle; they are used
    only to name genuinely co-occurring problems, never to invent a cascade.
    """
    peers = [p for p in (peers or []) if p is not anomaly]
    now = now or datetime.now(IST)

    train_number = _clean(anomaly.get("train_number"), "this train")
    train_name = _clean(anomaly.get("train_name"), "")
    station = _clean(
        anomaly.get("current_station") or anomaly.get("location"),
        "its last reported location",
    )
    destination = _clean(anomaly.get("destination"), "")
    delay = _int(anomaly.get("delay_minutes"))
    kind = str(anomaly.get("anomaly_type") or "delay").lower()
    load = str(anomaly.get("passenger_load") or "").lower()
    severity = str(anomaly.get("severity") or severity_for_delay(delay)).lower()
    label = f"{train_number} {train_name}".strip()
    observed_at = now.strftime("%H:%M IST")

    toward = f" toward {destination}" if destination else ""

    # --- What is happening -------------------------------------------------
    if kind == "cancellation":
        situation = (
            f"{label} is recorded as cancelled at {station} as of {observed_at}. "
            f"Passengers holding reservations on this service need re-accommodation{toward}."
        )
    elif kind == "overcrowding":
        situation = (
            f"{label} is reporting {load or 'excess'} loading at {station} as of {observed_at}"
            + (f", running {delay} min behind schedule" if delay else "")
            + ". Platform dwell and boarding time are the immediate constraint."
        )
    elif kind == "escalation":
        situation = (
            f"{label} is still unresolved at {station} and the delay has grown to {delay} min "
            f"as of {observed_at}. The previous response did not recover the run."
        )
    elif kind == "cascade":
        situation = (
            f"{label} is {delay} min behind schedule at {station} as of {observed_at}, "
            f"and it is one of several services degraded on the same corridor in this cycle."
        )
    else:
        situation = (
            f"{label} is running {delay} min behind schedule at {station} "
            f"as of {observed_at}{toward}."
        )

    # Co-occurring problems, named only when they are actually in this cycle.
    # Deduplicated: the same train can arrive twice in one cycle, once from the
    # detection rules and once as an escalation, and listing it twice reads as
    # two separate problems.
    peer_numbers = []
    for p in peers:
        number = str(p.get("train_number") or "")
        if number and number != train_number and number not in peer_numbers:
            peer_numbers.append(number)
    if peer_numbers:
        shown = ", ".join(peer_numbers[:4])
        more = f" and {len(peer_numbers) - 4} more" if len(peer_numbers) > 4 else ""
        situation += f" Detected in the same cycle: {shown}{more}."

    # --- What to do about it ----------------------------------------------
    if kind == "cancellation":
        operations_task = (
            f"Confirm the cancellation of {train_number} with the divisional control office and "
            f"identify the next available service{toward} for re-accommodation."
        )
        maintenance_task = (
            f"Release any stock and crew held for {train_number} at {station} and report "
            f"the rake's availability for the next working."
        )
        station_task = (
            f"Announce the cancellation of {label} at {station}, open the refund and "
            f"re-booking counter, and update the platform displays."
        )
        passenger_sms = (
            f"{label} has been cancelled. Please approach the station enquiry counter at "
            f"{station} for re-booking or a refund."
        )
        reroute_plan = f"No rerouting applies — {train_number} is cancelled. Re-accommodate passengers on the next service{toward}."
    elif kind == "overcrowding":
        operations_task = (
            f"Assess whether an additional coach or a relief service can be attached to "
            f"{train_number} at {station}; confirm the decision before departure clearance."
        )
        maintenance_task = (
            f"Have the rake examined at {station} before departure — check brake and door "
            f"operation under the reported {load or 'heavy'} loading."
        )
        station_task = (
            f"Deploy crowd control on the {station} platform for {train_number}, stagger "
            f"boarding by coach, and keep the foot overbridge clear."
        )
        passenger_sms = (
            f"{label} is heavily crowded at {station}. Please board only at your reserved "
            f"coach position and allow extra time."
        )
        reroute_plan = f"Hold {train_number} at {station} only as long as boarding requires; no diversion is warranted for loading alone."
    else:
        operations_task = (
            f"Re-slot {train_number} out of {station}{toward} and agree the crossing order "
            f"with the section controller before granting line clear."
        )
        maintenance_task = (
            f"Check the {station} approach — signalling, point machines and any speed "
            f"restriction — for what is holding {train_number}, and report back before the next cycle."
        )
        station_task = (
            f"Announce the {delay} min delay to {label} at {station}, hold the platform "
            f"assignment until operations confirm the new slot, and advise connecting passengers."
        )
        passenger_sms = (
            f"{label} is running about {delay} minutes late at {station}. "
            f"Please check the station display before travelling."
        )
        reroute_plan = (
            f"Give {train_number} priority pathing out of {station}{toward}. "
            f"Divert only if the section ahead is blocked — a diversion costs more than {delay} min on most alternatives."
        )

    # --- What happens if nobody acts ---------------------------------------
    outcome = recovery_estimate(delay)

    reasoning_steps = [
        f"Observed: {train_number} at {station}"
        + (f", {delay} min behind schedule" if delay else "")
        + (f", status {anomaly.get('status')}" if anomaly.get("status") else "")
        + ".",
        f"Classified: {kind} at {severity} severity"
        + (f" (delay over {_threshold_text(delay)})" if kind == "delay" and delay else "")
        + ".",
        f"Constraint: {station} is the point of control — the response has to be agreed there before the train can be released.",
        f"Chosen response: {reroute_plan}",
    ]
    if outcome:
        reasoning_steps.append(f"Expected: {outcome}")

    return {
        "situation_summary": situation,
        "reasoning_steps": reasoning_steps,
        "maintenance_task": maintenance_task,
        "operations_task": operations_task,
        "station_manager_task": station_task,
        "passenger_sms": passenger_sms,
        "reroute_plan": reroute_plan,
        "expected_outcome": outcome,
        "severity": severity,
    }


def _threshold_text(delay):
    for bound in (120, 60, 30, 15):
        if delay > bound:
            return f"{bound} min"
    return "15 min"
