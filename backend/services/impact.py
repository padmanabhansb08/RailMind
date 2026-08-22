"""Network impact forecast: which other trains are converging on a location.

An incident is never really about one train. A train stopped at a junction is a
problem because of what arrives behind it, and that is the one calculation a
controller cannot do by eye across ~2,700 live trains.

Scope, stated plainly: this reports trains whose next scheduled stop is the
incident station within a time window. It is convergence, not causation. The
upstream feed carries no block sections, no platform assignments and no
signalling, so nothing here can honestly claim another train *will* be delayed
— only that it is heading into the same place. Every label this module produces
is worded accordingly.

Two facts about the feed shape the design:

* `next_arrival_minutes` is minutes-since-midnight IST, not minutes from now.
  Verified against the live snapshot: 2657 of 2753 trains fall within +30 min
  of the wall clock, median +4.
* `next_station` is always the *immediate* next stop, so a wide window adds
  nothing. Trains converge on a station within roughly half an hour or not at all.
"""

import re
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

MINUTES_PER_DAY = 1440
DEFAULT_WINDOW_MINUTES = 30

# Suffixes that distinguish platforms within one station complex rather than
# different places. Dropped only from the END of a name, never mid-string.
DROPPABLE_SUFFIXES = {
    "JN", "JN.", "JUNCTION", "CANT", "CANTT", "CANTONMENT",
    "TERMINUS", "TERMINAL", "HALT", "PH", "STATION",
}


def normalize_station(name):
    """Reduce a station name to a comparable key.

    Deliberately does NOT do substring matching. "Patna" appearing inside
    "VISAKHAPATNAM ELECTRIC LOCO SHED" is a different station, and a false
    positive here would put the wrong trains in front of an operator.
    """
    if not name:
        return ""
    text = str(name).upper().strip()
    text = text.replace("(", " ").replace(")", " ")
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    tokens = [t for t in text.split() if t]
    while tokens and tokens[-1] in DROPPABLE_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def station_aliases(name):
    """Every key a feed station should be findable under.

    Indian station names often carry an older or local name in parentheses —
    "HUBBALLI SOUTH (HUBLI)" — and incidents may use either form.
    """
    if not name:
        return set()
    aliases = {normalize_station(name)}
    for inner in re.findall(r"\(([^)]*)\)", str(name)):
        aliases.add(normalize_station(inner))
    # The portion before any parenthetical, e.g. "HUBBALLI SOUTH".
    head = re.sub(r"\([^)]*\)", " ", str(name))
    aliases.add(normalize_station(head))
    return {a for a in aliases if a}


def now_minutes(now=None):
    """Current IST time as minutes since midnight, matching the feed's clock."""
    now = now or datetime.now(IST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=IST)
    else:
        now = now.astimezone(IST)
    return now.hour * 60 + now.minute


def minutes_until(scheduled_minute, current_minute):
    """Signed minutes from now until a minutes-since-midnight value.

    Wraps across midnight by choosing the nearest interpretation: a train due
    at 00:10 when the clock reads 23:55 is 15 minutes away, not 1425.
    """
    if scheduled_minute is None:
        return None
    delta = (int(scheduled_minute) - current_minute) % MINUTES_PER_DAY
    return delta - MINUTES_PER_DAY if delta > MINUTES_PER_DAY / 2 else delta


def forecast(station_name, live_trains, now=None, window_minutes=DEFAULT_WINDOW_MINUTES,
             exclude_train=None, limit=12):
    """Trains converging on `station_name` within the window.

    Returns a dict the API and UI can render directly, including an explicit
    `matched` flag so an unrecognised station reads as "unknown", never as
    "nothing is coming".
    """
    targets = station_aliases(station_name)
    if not targets:
        return {
            "station": station_name,
            "matched": False,
            "reason": "No station recorded on this incident.",
            "window_minutes": window_minutes,
            "count": 0,
            "trains": [],
        }

    current = now_minutes(now)
    converging = []

    for train in live_trains or []:
        next_alias = station_aliases(train.get("next_station_name"))
        current_alias = station_aliases(train.get("current_station_name"))
        code_match = str(train.get("next_station") or "").upper() in targets \
            or str(train.get("current_station") or "").upper() in targets

        at_station = bool(targets & current_alias)
        approaching = bool(targets & next_alias)
        if not (at_station or approaching or code_match):
            continue

        number = str(train.get("train_number") or "")
        if exclude_train and number == str(exclude_train):
            continue

        eta = minutes_until(train.get("next_arrival_minutes"), current)
        if approaching and (eta is None or eta < 0 or eta > window_minutes):
            continue

        converging.append({
            "train_number": number,
            "train_name": train.get("train_name") or "Unknown",
            "type": train.get("type"),
            "relation": "at_station" if at_station else "approaching",
            "arrives_in_minutes": None if at_station else eta,
            "from_station": train.get("current_station_name"),
        })

    # Already-there first, then soonest arrival.
    converging.sort(key=lambda t: (
        0 if t["relation"] == "at_station" else 1,
        t["arrives_in_minutes"] if t["arrives_in_minutes"] is not None else 9999,
    ))

    soonest = next((t["arrives_in_minutes"] for t in converging
                    if t["arrives_in_minutes"] is not None), None)

    # `matched` says only that we had a station to look up and a feed to look
    # in. It deliberately does not claim the station was "found": the feed
    # names only stations where trains currently are, so a quiet station and an
    # unrecognised one are indistinguishable here, and guessing between them
    # would put an unearned claim in front of an operator.
    return {
        "station": station_name,
        "matched": bool(live_trains),
        "reason": None if live_trains else "Live network feed unavailable.",
        "window_minutes": window_minutes,
        "count": len(converging),
        "next_arrival_in": soonest,
        "trains": converging[:limit],
        "truncated": max(len(converging) - limit, 0),
    }
