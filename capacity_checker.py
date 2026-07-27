"""
Capacity Checker — Phase 1 logic (single combined carers.csv, core/optional
windows, days-off support, overnight shift support, and double-handed calls)

Reads sample_data/clients.csv, sample_data/carers.csv (combined carer info +
availability windows), and answers:
  "Which carers are free on a given day/time for a given duration?"

Supports:
  - Multiple availability windows per carer per day (split shifts)
  - 'core' vs 'optional' windows
  - Day patterns with exclusions, e.g. 'Mon-Sun (minus Sat)'
  - Overnight shifts, e.g. 22:00-06:00 (end_time earlier than start_time
    means the shift crosses midnight)
  - Double-handed calls via 'carers_required' column (e.g. 2 carers needed)

This version does NOT use Google Maps yet — it only checks time availability
(no travel time). Travel-time awareness is added in Phase 2.

How to run:
    python capacity_checker.py

Requires: Python 3.8+ (no extra packages needed — uses only the standard library)
"""

import csv
import datetime
from dataclasses import dataclass
from typing import List, Optional
import re


# ---------------------------------------------------------------------------
# Data classes
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
    skills: str = ""


@dataclass
class CarerAvailability:
    carer_id: int
    day_pattern: str
    start_time: datetime.time
    end_time: datetime.time
    availability_type: str  # 'core' or 'optional'


@dataclass
class Call:
    call_id: int            # unique internal id, one per CSV row
    call_number: int        # original (possibly repeated) call_id from spreadsheet
    client_id: int
    day_pattern: str
    start_time: datetime.time
    end_time: datetime.time
    duration_minutes: int
    carers_required: int = 1


@dataclass
class Assignment:
    call_id: int
    carer_id: int


# ---------------------------------------------------------------------------
# Day pattern matching
# ---------------------------------------------------------------------------

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
    Returns True if `day` (e.g. 'Wed') falls inside `pattern`, which may be:
      - a single day: 'Thurs'
      - a simple range: 'Mon-Sun', 'Mon - Fri'
      - a range with exclusions: 'Mon - Sun (minus Sat)'
      - a comma/&/+/and separated list: 'Tues & Fri', 'Mon, Wed, Fri'
      - a multi-dash list (not a true range): 'Mon - Weds - Fri'
      - a space-separated list: 'Tues Weds Fri Sat Sun'
      - the shorthand 'M-S' meaning every day of the week
    """
    day = _normalise_day(day)
    if day is None:
        raise ValueError(f"Unrecognised day: {day}")

    pattern = pattern.strip()

    exclusions = []
    if "(" in pattern and ")" in pattern:
        main_part, exclusion_part = pattern.split("(", 1)
        exclusion_part = exclusion_part.replace(")", "")
        exclusion_part = exclusion_part.lower().replace("minus", "").replace("excl", "")
        exclusions = [
            _normalise_day(tok)
            for tok in re.split(r"[,&]", exclusion_part)
            if tok.strip()
        ]
        pattern = main_part.strip()

    if day in exclusions:
        return False

    # Shorthand meaning "every day of the week"
    if pattern.strip().upper() in ("M-S", "M - S"):
        return True

    # Normalise list separators
    normalised = re.sub(r"\s+and\s+", ",", pattern, flags=re.IGNORECASE)
    normalised = normalised.replace("&", ",").replace("+", ",")

    segments = [s.strip() for s in normalised.split(",") if s.strip()]
    for segment in segments:
        if _segment_matches_day(day, segment):
            return True
    return False


def _segment_matches_day(day: str, segment: str) -> bool:
    dash_count = segment.count("-")

    if dash_count == 0:
        tokens = segment.split()
        return any(_normalise_day(tok) == day for tok in tokens)

    if dash_count == 1:
        start_str, end_str = [p.strip() for p in segment.split("-", 1)]
        start_day = _normalise_day(start_str)
        end_day = _normalise_day(end_str)
        if start_day is None or end_day is None:
            raise ValueError(f"Unrecognised day pattern segment: {segment}")
        start_idx = DAY_ORDER.index(start_day)
        end_idx = DAY_ORDER.index(end_day)
        day_idx = DAY_ORDER.index(day)
        if start_idx <= end_idx:
            return start_idx <= day_idx <= end_idx
        return day_idx >= start_idx or day_idx <= end_idx

    tokens = [t.strip() for t in segment.split("-") if t.strip()]
    return any(_normalise_day(tok) == day for tok in tokens)


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def _parse_time(value: str) -> Optional[datetime.time]:
    value = value.strip()
    if not value:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Could not parse time: {value}")


def load_clients_and_calls(path: str):
    clients = {}
    calls = []
    next_call_id = 1

    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row["full_name"].strip()
            if name not in clients:
                client_id = len(clients) + 1
                clients[name] = Client(
                    client_id=client_id,
                    full_name=name,
                    postcode=row.get("postcode", "").strip(),
                )
            client_id = clients[name].client_id

            day_pattern = (row.get("day_pattern") or "").strip()
            start_time = _parse_time(row.get("start_time", ""))
            end_time = _parse_time(row.get("end_time", ""))
            duration_str = (row.get("duration_minutes") or "").strip()

            if not day_pattern or start_time is None or end_time is None or not duration_str:
                continue

            carers_required_str = (row.get("carers_required") or "1").strip()
            carers_required = int(carers_required_str) if carers_required_str else 1

            calls.append(
                Call(
                    call_id=next_call_id,
                    call_number=int(row["call_id"]),
                    client_id=client_id,
                    day_pattern=day_pattern,
                    start_time=start_time,
                    end_time=end_time,
                    duration_minutes=int(duration_str),
                    carers_required=carers_required,
                )
            )
            next_call_id += 1

    return list(clients.values()), calls


def load_carers_and_availability(path: str):
    carers = {}
    availability = []

    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            carer_id = int(row["carer_id"])
            if carer_id not in carers:
                carers[carer_id] = Carer(
                    carer_id=carer_id,
                    full_name=row["full_name"],
                    skills=row.get("skills", "") or "",
                )

            day_pattern = (row.get("day_pattern") or "").strip()
            start_time = _parse_time(row.get("start_time", ""))
            end_time = _parse_time(row.get("end_time", ""))

            if not day_pattern or start_time is None or end_time is None:
                continue

            availability.append(
                CarerAvailability(
                    carer_id=carer_id,
                    day_pattern=day_pattern,
                    start_time=start_time,
                    end_time=end_time,
                    availability_type=(row.get("availability_type") or "core").strip().lower(),
                )
            )

    return list(carers.values()), availability


# ---------------------------------------------------------------------------
# Core capacity-check logic
# ---------------------------------------------------------------------------

def _to_minutes(t: datetime.time) -> int:
    return t.hour * 60 + t.minute


def _overlaps(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_a < end_b and start_b < end_a


def _window_bounds(start_time: datetime.time, end_time: datetime.time):
    start = _to_minutes(start_time)
    end = _to_minutes(end_time)
    if end <= start:
        end += 24 * 60
    return start, end


class CapacityChecker:
    def __init__(
        self,
        clients: List[Client],
        carers: List[Carer],
        availability: List[CarerAvailability],
        calls: List[Call],
        assignments: List[Assignment],
    ):
        self.clients = {c.client_id: c for c in clients}
        self.carers = {c.carer_id: c for c in carers}
        self.availability = availability
        self.calls = {c.call_id: c for c in calls}
        self.assignments = assignments
        self.last_travel_check_errors = []

    def _windows_starting_on_day(self, carer_id: int, day: str) -> List[CarerAvailability]:
        result = [
            w for w in self.availability
            if w.carer_id == carer_id and day_matches_pattern(day, w.day_pattern)
        ]
        return sorted(result, key=lambda w: _to_minutes(w.start_time))

    @staticmethod
    def _previous_day(day: str) -> str:
        day = _normalise_day(day)
        idx = DAY_ORDER.index(day)
        return DAY_ORDER[(idx - 1) % 7]

    def windows_for_carer_on_day(self, carer_id: int, day: str):
        results = []

        for w in self._windows_starting_on_day(carer_id, day):
            start, end = _window_bounds(w.start_time, w.end_time)
            results.append((w, start, end))

        prev_day = self._previous_day(day)
        for w in self._windows_starting_on_day(carer_id, prev_day):
            start, end = _window_bounds(w.start_time, w.end_time)
            if end > 24 * 60:
                clipped_start = max(start - 24 * 60, 0)
                results.append((w, clipped_start, end - 24 * 60))

        return sorted(results, key=lambda item: item[1])

    def calls_for_carer_on_day(self, carer_id: int, day: str) -> List[Call]:
        result = []
        for a in self.assignments:
            if a.carer_id != carer_id:
                continue
            call = self.calls[a.call_id]
            if day_matches_pattern(day, call.day_pattern):
                result.append(call)
        return sorted(result, key=lambda c: _to_minutes(c.start_time))

    def check_carer_slot(
        self,
        carer_id: int,
        day: str,
        start_time: datetime.time,
        duration_minutes: int,
    ) -> Optional[str]:
        req_start = _to_minutes(start_time)
        req_end = req_start + duration_minutes

        for call in self.calls_for_carer_on_day(carer_id, day):
            call_start = _to_minutes(call.start_time)
            call_end = call_start + call.duration_minutes
            if _overlaps(req_start, req_end, call_start, call_end):
                return None

        best_match = None
        for window, w_start, w_end in self.windows_for_carer_on_day(carer_id, day):
            if req_start >= w_start and req_end <= w_end:
                if window.availability_type == "core":
                    return "core"
                best_match = "optional"

        return best_match

    def is_carer_free(self, carer_id: int, day: str, start_time: datetime.time, duration_minutes: int) -> bool:
        return self.check_carer_slot(carer_id, day, start_time, duration_minutes) is not None

    def find_available_carers(self, day: str, start_time: datetime.time, duration_minutes: int) -> List[tuple]:
        available = []
        for carer in self.carers.values():
            result = self.check_carer_slot(carer.carer_id, day, start_time, duration_minutes)
            if result is not None:
                available.append((carer, result))
        available.sort(key=lambda pair: 0 if pair[1] == "core" else 1)
        return available

    def free_slots_for_carer(self, carer_id: int, day: str) -> List[str]:
        busy = []
        for call in self.calls_for_carer_on_day(carer_id, day):
            call_start = _to_minutes(call.start_time)
            call_end = call_start + call.duration_minutes
            busy.append((call_start, call_end))
        busy.sort()

        def fmt(minutes: int) -> str:
            minutes = minutes % (24 * 60)
            return f"{minutes // 60:02d}:{minutes % 60:02d}"

        results = []
        for window, w_start, w_end in self.windows_for_carer_on_day(carer_id, day):
            cursor = w_start
            for call_start, call_end in busy:
                if call_end <= w_start or call_start >= w_end:
                    continue
                if call_start > cursor:
                    results.append(f"{fmt(cursor)}-{fmt(call_start)} ({window.availability_type})")
                cursor = max(cursor, call_end)
            if cursor < w_end:
                results.append(f"{fmt(cursor)}-{fmt(w_end)} ({window.availability_type})")

        return results

    def find_conflicts(self) -> List[tuple]:
        conflicts = []
        by_carer = {}
        for a in self.assignments:
            by_carer.setdefault(a.carer_id, []).append(self.calls[a.call_id])

        for carer_id, calls in by_carer.items():
            for i in range(len(calls)):
                for j in range(i + 1, len(calls)):
                    call_a, call_b = calls[i], calls[j]
                    if call_a.call_id == call_b.call_id:
                        continue
                    if not self._day_patterns_can_overlap(call_a.day_pattern, call_b.day_pattern):
                        continue
                    a_start = _to_minutes(call_a.start_time)
                    a_end = a_start + call_a.duration_minutes
                    b_start = _to_minutes(call_b.start_time)
                    b_end = b_start + call_b.duration_minutes
                    if _overlaps(a_start, a_end, b_start, b_end):
                        conflicts.append((call_a, call_b, self.carers[carer_id]))
        return conflicts

    def find_travel_conflicts(self, buffer_minutes: int = 0) -> List[tuple]:
        from travel_time import get_travel_time_minutes, TravelTimeError

        problems = []
        errors = []
        by_carer = {}
        for a in self.assignments:
            by_carer.setdefault(a.carer_id, []).append(self.calls[a.call_id])

        for carer_id, calls in by_carer.items():
            carer = self.carers[carer_id]
            for day in DAY_ORDER:
                day_calls = [c for c in calls if day_matches_pattern(day, c.day_pattern)]
                day_calls.sort(key=lambda c: _to_minutes(c.start_time))

                for i in range(len(day_calls) - 1):
                    call_a = day_calls[i]
                    call_b = day_calls[i + 1]

                    a_end = _to_minutes(call_a.start_time) + call_a.duration_minutes
                    b_start = _to_minutes(call_b.start_time)
                    gap_minutes = b_start - a_end

                    if gap_minutes < 0:
                        continue

                    postcode_a = self.clients[call_a.client_id].postcode
                    postcode_b = self.clients[call_b.client_id].postcode

                    try:
                        travel_minutes = get_travel_time_minutes(postcode_a, postcode_b)
                    except TravelTimeError as e:
                        errors.append((call_a, call_b, carer, day, str(e)))
                        continue

                    if gap_minutes < travel_minutes + buffer_minutes:
                        problems.append((call_a, call_b, carer, day, gap_minutes, travel_minutes))

        self.last_travel_check_errors = errors
        return problems

    def find_understaffed_calls(self) -> List[tuple]:
        assigned_by_call = {}
        for a in self.assignments:
            assigned_by_call.setdefault(a.call_id, set()).add(a.carer_id)

        understaffed = []
        for call in self.calls.values():
            assigned_count = len(assigned_by_call.get(call.call_id, set()))
            if assigned_count < call.carers_required:
                understaffed.append((call, call.carers_required, assigned_count))
        return sorted(understaffed, key=lambda item: item[0].call_id)

    @staticmethod
    def _day_patterns_can_overlap(pattern_a: str, pattern_b: str) -> bool:
        for day in DAY_ORDER:
            if day_matches_pattern(day, pattern_a) and day_matches_pattern(day, pattern_b):
                return True
        return False


if __name__ == "__main__":
    carers, availability = load_carers_and_availability("sample_data/carers.csv")
    clients, calls = load_clients_and_calls("sample_data/clients.csv")

    clients_by_id = {c.client_id: c for c in clients}
    client_18_calls = [c for c in calls if clients_by_id[c.client_id].full_name == "Client 18"]

    assignments = [
        Assignment(call_id=2, carer_id=8),
        Assignment(call_id=88, carer_id=8),
        Assignment(call_id=5, carer_id=8),
        Assignment(call_id=90, carer_id=7),
        Assignment(call_id=13, carer_id=8),
        Assignment(call_id=66, carer_id=8),
    ]

    if client_18_calls:
        assignments.append(Assignment(call_id=client_18_calls[0].call_id, carer_id=10))

    checker = CapacityChecker(clients, carers, availability, calls, assignments)

    print("=== Free slots for Adeyoluwa, Mary on Monday (overnight shift, real data) ===")
    for slot in checker.free_slots_for_carer(carer_id=2, day="Mon"):
        print(" ", slot)