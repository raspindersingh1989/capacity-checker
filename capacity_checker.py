"""
Capacity Checker — Phase 1 logic

Reads the sample_data CSVs (clients, carers, calls) and answers:
  "Which carers are free on a given day/time for a given duration?"

This version does NOT use Google Maps yet — it only checks time availability
(no travel time). This lets you test the core logic locally before adding
travel-time/postcode matching.

How to run:
    python capacity_checker.py

Requires: Python 3.8+ (no extra packages needed — uses only the standard library)
"""

import csv
import datetime
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Data classes — simple containers for each row of data
# ---------------------------------------------------------------------------

@dataclass
class Client:
    client_id: int
    full_name: str
    postcode: str


@dataclass
class Carer:
    carer_id: int
    full_name: str
    shift_start: datetime.time
    shift_end: datetime.time
    skills: str = ""


@dataclass
class Call:
    call_id: int
    client_id: int
    day_pattern: str
    start_time: datetime.time
    end_time: datetime.time
    duration_minutes: int


@dataclass
class Assignment:
    call_id: int
    carer_id: int


# ---------------------------------------------------------------------------
# Day pattern matching
# ---------------------------------------------------------------------------
# Your spreadsheet uses patterns like:
#   "Mon-Sun", "Mon-Sun (minus Tues)", "Thurs", "Friday", "Tues-Sun"
# This function checks whether a given weekday name matches a pattern.

DAY_ORDER = ["Mon", "Tues", "Wed", "Thurs", "Fri", "Sat", "Sun"]

DAY_ALIASES = {
    "mon": "Mon", "monday": "Mon",
    "tue": "Tues", "tues": "Tues", "tuesday": "Tues",
    "wed": "Wed", "wednesday": "Wed",
    "thu": "Thurs", "thur": "Thurs", "thurs": "Thurs", "thursday": "Thurs",
    "fri": "Fri", "friday": "Fri",
    "sat": "Sat", "saturday": "Sat",
    "sun": "Sun", "sunday": "Sun",
}


def _normalise_day(token: str) -> Optional[str]:
    return DAY_ALIASES.get(token.strip().lower())


def day_matches_pattern(day: str, pattern: str) -> bool:
    """
    Returns True if `day` (e.g. 'Wed') falls inside `pattern`
    (e.g. 'Mon-Sun (minus Tues)', 'Thurs', 'Tues-Sun').
    """
    day = _normalise_day(day)
    if day is None:
        raise ValueError(f"Unrecognised day: {day}")

    pattern = pattern.strip()

    # Split off any "(minus X, Y)" exclusion clause
    exclusions = []
    if "(" in pattern and ")" in pattern:
        main_part, exclusion_part = pattern.split("(", 1)
        exclusion_part = exclusion_part.replace(")", "")
        exclusion_part = exclusion_part.lower().replace("minus", "")
        exclusions = [
            _normalise_day(tok) for tok in exclusion_part.split(",") if tok.strip()
        ]
        pattern = main_part.strip()
    else:
        pattern = pattern.strip()

    if day in exclusions:
        return False

    # Single day, e.g. "Thurs" or "Friday"
    if "-" not in pattern:
        return _normalise_day(pattern) == day

    # Range, e.g. "Mon-Sun", "Tues-Sun"
    start_str, end_str = [p.strip() for p in pattern.split("-", 1)]
    start_day = _normalise_day(start_str)
    end_day = _normalise_day(end_str)
    if start_day is None or end_day is None:
        raise ValueError(f"Unrecognised day pattern: {pattern}")

    start_idx = DAY_ORDER.index(start_day)
    end_idx = DAY_ORDER.index(end_day)
    day_idx = DAY_ORDER.index(day)

    if start_idx <= end_idx:
        return start_idx <= day_idx <= end_idx
    else:
        # wraps around the week, e.g. "Sat-Mon"
        return day_idx >= start_idx or day_idx <= end_idx


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def _parse_time(value: str) -> datetime.time:
    value = value.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Could not parse time: {value}")


def load_clients(path: str) -> List[Client]:
    clients = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            clients.append(
                Client(
                    client_id=int(row["client_id"]),
                    full_name=row["full_name"],
                    postcode=row["postcode"],
                )
            )
    return clients


def load_carers(path: str) -> List[Carer]:
    carers = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            carers.append(
                Carer(
                    carer_id=int(row["carer_id"]),
                    full_name=row["full_name"],
                    shift_start=_parse_time(row["shift_start"]),
                    shift_end=_parse_time(row["shift_end"]),
                    skills=row.get("skills", "") or "",
                )
            )
    return carers


def load_calls(path: str) -> List[Call]:
    calls = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            calls.append(
                Call(
                    call_id=int(row["call_id"]),
                    client_id=int(row["client_id"]),
                    day_pattern=row["day_pattern"],
                    start_time=_parse_time(row["start_time"]),
                    end_time=_parse_time(row["end_time"]),
                    duration_minutes=int(row["duration_minutes"]),
                )
            )
    return calls


# ---------------------------------------------------------------------------
# Core capacity-check logic
# ---------------------------------------------------------------------------

def _to_minutes(t: datetime.time) -> int:
    return t.hour * 60 + t.minute


def _overlaps(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_a < end_b and start_b < end_a


class CapacityChecker:
    """
    Loads clients/carers/calls/assignments and answers availability questions.

    NOTE: This version ignores travel time and postcode distance —
    it only checks whether a carer's shift + existing calls leave a free
    slot on the requested day/time. Travel-time awareness is added in Phase 2
    once Google Maps is wired in.
    """

    def __init__(
        self,
        clients: List[Client],
        carers: List[Carer],
        calls: List[Call],
        assignments: List[Assignment],
    ):
        self.clients = {c.client_id: c for c in clients}
        self.carers = {c.carer_id: c for c in carers}
        self.calls = {c.call_id: c for c in calls}
        self.assignments = assignments

    def calls_for_carer_on_day(self, carer_id: int, day: str) -> List[Call]:
        """All calls assigned to this carer that occur on the given weekday."""
        result = []
        for a in self.assignments:
            if a.carer_id != carer_id:
                continue
            call = self.calls[a.call_id]
            if day_matches_pattern(day, call.day_pattern):
                result.append(call)
        return sorted(result, key=lambda c: _to_minutes(c.start_time))

    def is_carer_free(
        self,
        carer_id: int,
        day: str,
        start_time: datetime.time,
        duration_minutes: int,
    ) -> bool:
        """True if the carer's shift covers this window and no existing call overlaps it."""
        carer = self.carers[carer_id]
        req_start = _to_minutes(start_time)
        req_end = req_start + duration_minutes

        shift_start = _to_minutes(carer.shift_start)
        shift_end = _to_minutes(carer.shift_end)
        if req_start < shift_start or req_end > shift_end:
            return False  # outside working hours

        for call in self.calls_for_carer_on_day(carer_id, day):
            call_start = _to_minutes(call.start_time)
            call_end = call_start + call.duration_minutes
            if _overlaps(req_start, req_end, call_start, call_end):
                return False

        return True

    def find_available_carers(
        self,
        day: str,
        start_time: datetime.time,
        duration_minutes: int,
    ) -> List[Carer]:
        """Returns every carer who is free for the requested slot (ignoring travel time)."""
        available = []
        for carer in self.carers.values():
            if self.is_carer_free(carer.carer_id, day, start_time, duration_minutes):
                available.append(carer)
        return available

    def free_slots_for_carer(self, carer_id: int, day: str) -> List[str]:
        """
        Returns a simple list of free time windows for a carer on a given day,
        as human-readable strings, e.g. ['08:35-09:00', '09:45-17:00'].
        """
        carer = self.carers[carer_id]
        shift_start = _to_minutes(carer.shift_start)
        shift_end = _to_minutes(carer.shift_end)

        busy = []
        for call in self.calls_for_carer_on_day(carer_id, day):
            call_start = _to_minutes(call.start_time)
            call_end = call_start + call.duration_minutes
            busy.append((call_start, call_end))
        busy.sort()

        free_windows = []
        cursor = shift_start
        for call_start, call_end in busy:
            if call_start > cursor:
                free_windows.append((cursor, call_start))
            cursor = max(cursor, call_end)
        if cursor < shift_end:
            free_windows.append((cursor, shift_end))

        def fmt(minutes: int) -> str:
            return f"{minutes // 60:02d}:{minutes % 60:02d}"

        return [f"{fmt(s)}-{fmt(e)}" for s, e in free_windows if e > s]


# ---------------------------------------------------------------------------
# Demo / manual test when run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    clients = load_clients("sample_data/clients.csv")
    carers = load_carers("sample_data/carers.csv")
    calls = load_calls("sample_data/calls.csv")

    # Sample assignments matching the screenshots (carer_id, call_id) pairs.
    # In the real system this table comes from the 'Carer Assigned' column.
    assignments = [
        Assignment(call_id=11, carer_id=6),  # Kaur, Harpreet -> Pearce, Lynn 08:15
        Assignment(call_id=12, carer_id=6),  # Kaur, Harpreet -> Pearce, Lynn Friday 12:00
        Assignment(call_id=4, carer_id=3),   # Bhachoo, Hardeep -> Adshead, Lois
        Assignment(call_id=5, carer_id=3),
    ]

    checker = CapacityChecker(clients, carers, calls, assignments)

    print("=== Free slots for Kaur, Harpreet on Monday ===")
    for slot in checker.free_slots_for_carer(carer_id=6, day="Mon"):
        print(" ", slot)

    print()
    print("=== Who is free Wednesday 14:00 for 30 minutes? ===")
    available = checker.find_available_carers(
        day="Wed", start_time=datetime.time(14, 0), duration_minutes=30
    )
    for carer in available:
        print(" ", carer.full_name)
