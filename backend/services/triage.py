"""Turns the raw incident log into a ranked operator decision queue.

Two jobs: collapse repeats of the same underlying problem into one card, and
order what's left by how much it deserves a human right now.

Every ranking input is a value actually recorded on the incident — severity,
delay, how often it has recurred, how long it has sat unanswered. Nothing is
estimated. A tempting signal like "passengers affected" is deliberately absent
because the pipeline never measures it, and a plausible invented number is
worse than no number: it would drive real triage decisions.

Because operators need to trust the order, `score_breakdown` reports what each
factor contributed, so a card's position is always explainable.
"""

from datetime import datetime

# Severity vocabulary is inconsistent across the pipeline (the LLM path emits
# critical/warning/info, the heuristic path emits high/medium/low), so both are
# mapped onto one scale.
SEVERITY_WEIGHT = {
    "critical": 100,
    "high": 80,
    "severe": 80,
    "severely_delayed": 80,
    "warning": 50,
    "medium": 50,
    "low": 20,
    "info": 10,
}

SEVERITY_RANK = {"critical": 0, "high": 1, "severe": 1, "warning": 2, "medium": 2, "low": 3, "info": 4}

# Caps stop one runaway value from dominating the ordering.
MAX_DELAY_CONSIDERED = 240      # minutes
MAX_AGE_CONSIDERED = 240        # minutes
DELAY_WEIGHT = 0.5              # per minute, up to +120
AGE_WEIGHT = 0.25               # per minute, up to +60
RECURRENCE_WEIGHT = 15          # per extra occurrence
NETWORK_WEIGHT = 12             # per train converging on the same station
MAX_NETWORK_POINTS = 60         # a busy junction shouldn't eclipse severity

OPEN_STATUSES = {"pending", "", None}


def parse_time(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except Exception:
        return None


def group_key(incident):
    """What counts as 'the same problem recurring'.

    Same train at the same station is treated as one situation. Severity is
    excluded from the key so an escalating problem stays a single card rather
    than splitting into one per severity level.
    """
    return (
        str(incident.get("train_number") or "unknown"),
        str(incident.get("current_station") or incident.get("location") or "unknown").strip().lower(),
    )


def build_card(group, now):
    """Collapse one group of repeats into a single ranked decision card."""
    # Newest incident is the representative — it carries the current plan.
    ordered = sorted(group, key=lambda i: parse_time(i.get("timestamp")) or datetime.min, reverse=True)
    latest = ordered[0]
    oldest = ordered[-1]

    raised_at = parse_time(latest.get("timestamp"))
    first_seen_at = parse_time(oldest.get("timestamp"))
    age_minutes = max((now - raised_at).total_seconds() / 60, 0) if raised_at else 0

    severity = str(latest.get("severity") or "info").lower()
    delay = latest.get("delay_minutes") or 0
    try:
        delay = float(delay)
    except (TypeError, ValueError):
        delay = 0
    recurrence = len(group)

    severity_points = SEVERITY_WEIGHT.get(severity, 10)
    delay_points = min(delay, MAX_DELAY_CONSIDERED) * DELAY_WEIGHT
    recurrence_points = (recurrence - 1) * RECURRENCE_WEIGHT
    age_points = min(age_minutes, MAX_AGE_CONSIDERED) * AGE_WEIGHT

    breakdown = [
        {"factor": "Severity", "value": severity, "points": round(severity_points, 1)},
        {"factor": "Delay", "value": f"{int(delay)} min", "points": round(delay_points, 1)},
        {"factor": "Recurrence", "value": f"{recurrence}x", "points": round(recurrence_points, 1)},
        {"factor": "Unanswered", "value": humanize_minutes(age_minutes), "points": round(age_points, 1)},
    ]
    score = sum(b["points"] for b in breakdown)

    # The department tasks that dispatch if this plan is approved. This is the
    # concrete consequence of clicking the button, so it belongs on the card.
    dispatches = [
        {"department": "Maintenance", "task": latest.get("maintenance_task")},
        {"department": "Operations", "task": latest.get("operations_task")},
        {"department": "Station Manager", "task": latest.get("station_manager_task")},
    ]
    dispatches = [d for d in dispatches if d["task"]]

    return {
        "id": latest.get("incident_id") or latest.get("_id"),
        "duplicate_ids": [i.get("incident_id") or i.get("_id") for i in ordered[1:]],
        "train_number": latest.get("train_number"),
        "train_name": latest.get("train_name"),
        "station": latest.get("current_station"),
        "severity": severity,
        "delay_minutes": int(delay),
        "title": latest.get("incident_title") or latest.get("summary"),
        "situation_summary": latest.get("situation_summary") or latest.get("summary"),
        "proposed_plan": latest.get("reroute_plan"),
        "dispatches": dispatches,
        "passenger_sms": latest.get("passenger_sms"),
        "resolution_status": latest.get("resolution_status") or "pending",
        "decisions": latest.get("decisions") or [],
        "raised_at": raised_at.isoformat() if raised_at else None,
        "first_seen_at": first_seen_at.isoformat() if first_seen_at else None,
        "age_minutes": int(age_minutes),
        "age_label": humanize_minutes(age_minutes),
        "recurrence": recurrence,
        "score": round(score, 1),
        "score_breakdown": breakdown,
        "inaction_note": inaction_note(delay, recurrence, age_minutes),
        "consequences": consequences(
            ordered, latest, delay, recurrence, age_minutes, len(dispatches)
        ),
        "reasoning_steps": latest.get("reasoning_steps") or [],
        "confidence_score": latest.get("confidence_score"),
        "memory_used": latest.get("memory_used"),
        "passenger_sms_plan": latest.get("passenger_sms"),
        "simulated": bool(latest.get("simulated")),
    }


def delay_of(incident):
    try:
        return float(incident.get("delay_minutes") or 0)
    except (TypeError, ValueError):
        return 0.0


def consequences(ordered, latest, delay, recurrence, age_minutes, dispatch_count):
    """What continues to be true while nobody decides.

    Every entry is derived from something the pipeline actually recorded — the
    current delay, how it moved across repeats, how long the card has sat, and
    how much work is held behind the approval. Nothing here is projected: a
    made-up "3 more trains will be late by 14:30" would read as a forecast and
    drive real decisions off a number nobody measured.
    """
    items = []
    station = latest.get("current_station") or latest.get("location") or "its current location"
    train = latest.get("train_number") or "This train"

    if delay:
        items.append({
            "kind": "delay",
            "headline": f"{train} stays {int(delay)} min behind schedule",
            "detail": f"Last recorded at {station}. Every downstream arrival on this run inherits the same {int(delay)} min.",
        })
    else:
        items.append({
            "kind": "delay",
            "headline": "No delay recorded yet on this train",
            "detail": f"Raised at {station} on a non-delay rule.",
        })

    # Trend across the repeats of this same situation, oldest to newest.
    if recurrence > 1:
        first_delay = delay_of(ordered[-1])
        if delay > first_delay:
            items.append({
                "kind": "trend",
                "headline": f"Delay is growing — {int(first_delay)} min to {int(delay)} min across {recurrence} logs",
                "detail": "Each cycle since the first report has made this worse, not better.",
            })
        elif delay < first_delay:
            items.append({
                "kind": "trend",
                "headline": f"Delay is recovering — {int(first_delay)} min down to {int(delay)} min",
                "detail": f"Still logged {recurrence} times without a decision.",
            })
        else:
            items.append({
                "kind": "trend",
                "headline": f"Same situation logged {recurrence} times and unchanged",
                "detail": "Repeat reports mean the condition is persisting, not clearing on its own.",
            })

    if dispatch_count:
        items.append({
            "kind": "dispatch",
            "headline": f"{dispatch_count} department task{'' if dispatch_count == 1 else 's'} stay unassigned",
            "detail": "Maintenance, operations and station staff are not dispatched until this plan is approved.",
        })

    if age_minutes >= 1:
        items.append({
            "kind": "age",
            "headline": f"Unanswered for {humanize_minutes(age_minutes)}",
            "detail": "No operator decision is on record against this incident.",
        })

    return items


def humanize_minutes(minutes):
    """Render an age a human can read at a glance."""
    minutes = int(minutes)
    if minutes < 60:
        return f"{minutes} min"
    if minutes < 1440:
        hours = minutes / 60
        return f"{hours:.0f} hr" if hours >= 2 else f"{hours:.1f} hr"
    days = minutes / 1440
    return f"{days:.0f} days" if days >= 2 else f"{days:.1f} days"


def inaction_note(delay, recurrence, age_minutes):
    """State the current cost of not deciding, using only recorded facts."""
    parts = []
    if delay:
        parts.append(f"train is {int(delay)} min behind schedule")
    if recurrence > 1:
        parts.append(f"same situation logged {recurrence} times and still unresolved")
    if age_minutes >= 1:
        parts.append(f"no decision recorded for {humanize_minutes(age_minutes)}")
    if not parts:
        return "Newly raised; no delay recorded yet."
    return "If nothing is done: " + "; ".join(parts) + "."


def apply_network_impact(cards, live_trains, window_minutes=None):
    """Fold converging-train counts into each card's score and re-rank.

    An identical delay matters more where six trains are heading into the same
    station than where none are, and that comparison is invisible in the raw
    incident log.

    Applied as a separate pass so the queue still works when the live network
    feed is unavailable — in that case cards simply keep their base score
    rather than silently ranking as if nothing were converging.
    """
    from .impact import forecast, DEFAULT_WINDOW_MINUTES

    window = window_minutes or DEFAULT_WINDOW_MINUTES
    if not live_trains:
        return cards

    for card in cards:
        try:
            result = forecast(
                card.get("station"), live_trains,
                window_minutes=window, exclude_train=card.get("train_number"),
            )
        except Exception:
            continue

        card["network_impact"] = result
        if not result["matched"] or result["count"] == 0:
            continue

        # Convergence is the one consequence the live feed can evidence, so it
        # joins the "if nothing is decided" list — worded as scheduling
        # pressure, never as a claim that these trains will be delayed.
        soonest = result.get("next_arrival_in")
        card.setdefault("consequences", []).append({
            "kind": "network",
            "headline": f"{result['count']} other train{'' if result['count'] == 1 else 's'} "
                        f"scheduled into {result['station']} within {result['window_minutes']} min",
            "detail": (f"Nearest is due in {soonest} min. " if soonest is not None else "")
                      + "The feed carries no platform or block data, so this is converging traffic, not a predicted knock-on delay.",
        })

        points = min(result["count"] * NETWORK_WEIGHT, MAX_NETWORK_POINTS)
        card["score_breakdown"].append({
            "factor": "Network impact",
            "value": f"{result['count']} converging",
            "points": round(points, 1),
        })
        card["score"] = round(card["score"] + points, 1)

    cards.sort(key=lambda c: (
        -c["score"],
        SEVERITY_RANK.get(c["severity"], 9),
        c["raised_at"] or "",
    ))
    return cards


def build_queue(incidents, now=None, include_resolved=False):
    """Group, rank, and return the decision queue, highest priority first."""
    now = now or datetime.utcnow()

    groups = {}
    for inc in incidents:
        status = (inc.get("resolution_status") or "pending").lower()
        if not include_resolved and status not in OPEN_STATUSES:
            continue
        groups.setdefault(group_key(inc), []).append(inc)

    cards = [build_card(group, now) for group in groups.values()]
    # Score first; severity rank then recency break ties so ordering is stable.
    cards.sort(key=lambda c: (
        -c["score"],
        SEVERITY_RANK.get(c["severity"], 9),
        c["raised_at"] or "",
    ))
    return cards
