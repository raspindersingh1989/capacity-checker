"""
<<<<<<< HEAD
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
=======
Capacity Checker — Phase 1 logic

Reads the sample_data CSVs (clients, carers, calls) and answers:
  "Which carers are free on a given day/time for a given duration?"

This version does NOT use Google Maps yet — it only checks time availability
(no travel time). This lets you test the core logic locally before adding
travel-time/postcode matching.
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c

How to run:
    python capacity_checker.py

Requires: Python 3.8+ (no extra packages needed — uses only the standard library)
"""

import csv
import datetime
<<<<<<< HEAD
from dataclasses import dataclass
from typing import List, Optional
import re  # add this near the top of the file with the other imports

# ---------------------------------------------------------------------------
# Data classes
=======
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Data classes — simple containers for each row of data
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
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
<<<<<<< HEAD
=======
    shift_start: datetime.time
    shift_end: datetime.time
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
    skills: str = ""


@dataclass
<<<<<<< HEAD
class CarerAvailability:
    carer_id: int
    day_pattern: str
    start_time: datetime.time
    end_time: datetime.time
    availability_type: str  # 'core' or 'optional'


@dataclass
class Call:
    call_id: int           # unique internal id, one per CSV row
    call_number: int        # the original (repeated) call_id from the spreadsheet
=======
class Call:
    call_id: int
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
    client_id: int
    day_pattern: str
    start_time: datetime.time
    end_time: datetime.time
    duration_minutes: int
<<<<<<< HEAD
    carers_required: int = 1  # how many carers this call needs (double-handed = 2)
=======
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c


@dataclass
class Assignment:
    call_id: int
    carer_id: int


# ---------------------------------------------------------------------------
# Day pattern matching
# ---------------------------------------------------------------------------
<<<<<<< HEAD
=======
# Your spreadsheet uses patterns like:
#   "Mon-Sun", "Mon-Sun (minus Tues)", "Thurs", "Friday", "Tues-Sun"
# This function checks whether a given weekday name matches a pattern.
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c

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
<<<<<<< HEAD
    Returns True if `day` (e.g. 'Wed') falls inside `pattern`, which may be:
      - a single day: 'Thurs'
      - a simple range: 'Mon-Sun', 'Mon - Fri'
      - a range with exclusions: 'Mon - Sun (minus Sat)'
      - a comma/&/+/and separated list: 'Tues & Fri', 'Mon, Wed, Fri'
      - a multi-dash list (not a true range): 'Mon - Weds - Fri'
      - a space-separated list: 'Tues Weds Fri Sat Sun'
      - the shorthand 'M-S' meaning every day of the week
=======
    Returns True if `day` (e.g. 'Wed') falls inside `pattern`
    (e.g. 'Mon-Sun (minus Tues)', 'Thurs', 'Tues-Sun').
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
    """
    day = _normalise_day(day)
    if day is None:
        raise ValueError(f"Unrecognised day: {day}")

    pattern = pattern.strip()

<<<<<<< HEAD
    # Handle exclusions in parentheses, e.g. "Mon - Sun (minus Sat)"
=======
    # Split off any "(minus X, Y)" exclusion clause
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
    exclusions = []
    if "(" in pattern and ")" in pattern:
        main_part, exclusion_part = pattern.split("(", 1)
        exclusion_part = exclusion_part.replace(")", "")
<<<<<<< HEAD
        exclusion_part = exclusion_part.lower().replace("minus", "").replace("excl", "")
        exclusions = [
            _normalise_day(tok)
            for tok in re.split(r"[,&]", exclusion_part)
            if tok.strip()
        ]
        pattern = main_part.strip()
=======
        exclusion_part = exclusion_part.lower().replace("minus", "")
        exclusions = [
            _normalise_day(tok) for tok in exclusion_part.split(",") if tok.strip()
        ]
        pattern = main_part.strip()
    else:
        pattern = pattern.strip()
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c

    if day in exclusions:
        return False

<<<<<<< HEAD
    # Shorthand meaning "every day of the week"
    if pattern.strip().upper() in ("M-S", "M - S"):
        return True

    # Normalise list separators ("and", "&", "+") to commas
    normalised = re.sub(r"\s+and\s+", ",", pattern, flags=re.IGNORECASE)
    normalised = normalised.replace("&", ",").replace("+", ",")

    segments = [s.strip() for s in normalised.split(",") if s.strip()]

    for segment in segments:
        if _segment_matches_day(day, segment):
            return True
    return False


def _segment_matches_day(day: str, segment: str) -> bool:
    """Checks whether `day` matches a single comma-separated segment of a pattern."""
    dash_count = segment.count("-")

    if dash_count == 0:
        # Either a single day, or a space-separated list of days
        tokens = segment.split()
        for tok in tokens:
            if _normalise_day(tok) == day:
                return True
        return False

    if dash_count == 1:
        # A genuine range, e.g. "Mon-Fri" or "Tues-Sun"
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
        else:
            return day_idx >= start_idx or day_idx <= end_idx

    # More than one dash — not a real range, e.g. "Mon - Weds - Fri" means
    # "Mon, Weds, Fri" individually, not a chained range.
    tokens = [t.strip() for t in segment.split("-") if t.strip()]
    for tok in tokens:
        if _normalise_day(tok) == day:
            return True
    return False

def _next_day(day: str) -> str:
    """Returns the day after `day`, e.g. 'Mon' -> 'Tues'."""
    day = _normalise_day(day)
    idx = DAY_ORDER.index(day)
    return DAY_ORDER[(idx + 1) % 7]
=======
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
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

<<<<<<< HEAD
def _parse_time(value: str) -> Optional[datetime.time]:
    value = value.strip()
    if not value:
        return None
=======
def _parse_time(value: str) -> datetime.time:
    value = value.strip()
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Could not parse time: {value}")


<<<<<<< HEAD
def load_clients_and_calls(path: str):
    """
    Reads the combined clients.csv (one row per call, client info repeated
    on each row) and returns two lists: unique Client records, and Call rows.

    NOTE: the spreadsheet's own 'call_id' column is NOT unique per row (the
    same client can have several rows sharing the same call_id, e.g. one per
    day of the week). So each Call gets its own unique internal `call_id`
    here (one per CSV row), and the original spreadsheet number is kept
    separately as `call_number` for reference/display only.

    The 'carers_required' column (default 1) marks double-handed calls that
    need more than one carer at the same time.
    """
    clients = {}
    calls = []
    next_call_id = 1
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row["full_name"].strip()
            if name not in clients:
                client_id = len(clients) + 1  # auto-assign a stable internal id
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
                continue  # no call entered yet for this client row

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
    """
    Reads the combined carers.csv (one row per availability window) and
    returns two lists: unique Carer records, and CarerAvailability windows.
    Rows with blank day_pattern/start_time/end_time (carer has no availability
    entered yet) are skipped for availability, but the carer is still created.
    """
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
                continue  # no availability entered yet for this row

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
=======
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
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c


# ---------------------------------------------------------------------------
# Core capacity-check logic
# ---------------------------------------------------------------------------

def _to_minutes(t: datetime.time) -> int:
    return t.hour * 60 + t.minute


def _overlaps(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_a < end_b and start_b < end_a


<<<<<<< HEAD
def _window_bounds(start_time: datetime.time, end_time: datetime.time):
    """
    Returns (start_minutes, end_minutes) for a window, where end_minutes may
    be >= 1440 (24*60) if the window crosses midnight, e.g. 22:00-06:00
    becomes (1320, 1800) -- i.e. it "ends" at 06:00 the NEXT day.
    """
    start = _to_minutes(start_time)
    end = _to_minutes(end_time)
    if end <= start:
        end += 24 * 60  # crosses midnight
    return start, end


class CapacityChecker:
    """
    Loads clients/carers/availability/calls/assignments and answers
    availability questions, including 'core' vs 'optional' windows,
    days off, overnight shifts, and double-handed staffing checks.

    NOTE: This version ignores travel time and postcode distance —
    it only checks whether a carer's availability windows + existing calls
    leave a free slot on the requested day/time.
=======
class CapacityChecker:
    """
    Loads clients/carers/calls/assignments and answers availability questions.

    NOTE: This version ignores travel time and postcode distance —
    it only checks whether a carer's shift + existing calls leave a free
    slot on the requested day/time. Travel-time awareness is added in Phase 2
    once Google Maps is wired in.
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
    """

    def __init__(
        self,
        clients: List[Client],
        carers: List[Carer],
<<<<<<< HEAD
        availability: List[CarerAvailability],
=======
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
        calls: List[Call],
        assignments: List[Assignment],
    ):
        self.clients = {c.client_id: c for c in clients}
        self.carers = {c.carer_id: c for c in carers}
<<<<<<< HEAD
        self.availability = availability
        self.calls = {c.call_id: c for c in calls}
        self.assignments = assignments

    def _windows_starting_on_day(self, carer_id: int, day: str) -> List[CarerAvailability]:
        result = [
            w
            for w in self.availability
            if w.carer_id == carer_id and day_matches_pattern(day, w.day_pattern)
        ]
        return sorted(result, key=lambda w: _to_minutes(w.start_time))

    def windows_for_carer_on_day(self, carer_id: int, day: str):
        """
        Returns windows active during `day`, including overnight windows that
        STARTED THE PREVIOUS DAY and spill into this day's early hours.
        Each item is (window, start_minutes, end_minutes) where the minutes
        are relative to the start of `day` at 00:00 (clipped to 0 if the
        window started the previous evening, or >=1440 if it runs into the
        next day).
        """
        results = []

        # Windows that start on this day
        for w in self._windows_starting_on_day(carer_id, day):
            start, end = _window_bounds(w.start_time, w.end_time)
            results.append((w, start, end))

        # Windows that started YESTERDAY and cross midnight into today
        prev_day = self._previous_day(day)
        for w in self._windows_starting_on_day(carer_id, prev_day):
            start, end = _window_bounds(w.start_time, w.end_time)
            if end > 24 * 60:  # it spilled into today
                # Clip the start to 00:00 of *today* (0 minutes) instead of
                # leaving it negative, otherwise this window ends up looking
                # identical to a fresh window that also starts on this day.
                clipped_start = max(start - 24 * 60, 0)
                results.append((w, clipped_start, end - 24 * 60))

        return sorted(results, key=lambda item: item[1])

    @staticmethod
    def _previous_day(day: str) -> str:
        day = _normalise_day(day)
        idx = DAY_ORDER.index(day)
        return DAY_ORDER[(idx - 1) % 7]

    def calls_for_carer_on_day(self, carer_id: int, day: str) -> List[Call]:
=======
        self.calls = {c.call_id: c for c in calls}
        self.assignments = assignments

    def calls_for_carer_on_day(self, carer_id: int, day: str) -> List[Call]:
        """All calls assigned to this carer that occur on the given weekday."""
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
        result = []
        for a in self.assignments:
            if a.carer_id != carer_id:
                continue
            call = self.calls[a.call_id]
            if day_matches_pattern(day, call.day_pattern):
                result.append(call)
        return sorted(result, key=lambda c: _to_minutes(c.start_time))

<<<<<<< HEAD
    def check_carer_slot(
=======
    def is_carer_free(
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
        self,
        carer_id: int,
        day: str,
        start_time: datetime.time,
        duration_minutes: int,
<<<<<<< HEAD
    ) -> Optional[str]:
        """
        Returns 'core', 'optional', or None (not free) for the requested slot.
        """
        req_start = _to_minutes(start_time)
        req_end = req_start + duration_minutes

=======
    ) -> bool:
        """True if the carer's shift covers this window and no existing call overlaps it."""
        carer = self.carers[carer_id]
        req_start = _to_minutes(start_time)
        req_end = req_start + duration_minutes

        shift_start = _to_minutes(carer.shift_start)
        shift_end = _to_minutes(carer.shift_end)
        if req_start < shift_start or req_end > shift_end:
            return False  # outside working hours

>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
        for call in self.calls_for_carer_on_day(carer_id, day):
            call_start = _to_minutes(call.start_time)
            call_end = call_start + call.duration_minutes
            if _overlaps(req_start, req_end, call_start, call_end):
<<<<<<< HEAD
                return None

        best_match = None
        for window, w_start, w_end in self.windows_for_carer_on_day(carer_id, day):
            if req_start >= w_start and req_end <= w_end:
                if window.availability_type == "core":
                    return "core"
                best_match = "optional"

        return best_match

    def is_carer_free(
        self, carer_id: int, day: str, start_time: datetime.time, duration_minutes: int
    ) -> bool:
        return self.check_carer_slot(carer_id, day, start_time, duration_minutes) is not None

    def find_available_carers(
        self, day: str, start_time: datetime.time, duration_minutes: int
    ) -> List[tuple]:
        """
        Returns a list of (Carer, availability_type) sorted so 'core' matches
        come before 'optional' matches.
        """
        available = []
        for carer in self.carers.values():
            result = self.check_carer_slot(carer.carer_id, day, start_time, duration_minutes)
            if result is not None:
                available.append((carer, result))
        available.sort(key=lambda pair: 0 if pair[1] == "core" else 1)
        return available

    def free_slots_for_carer(self, carer_id: int, day: str) -> List[str]:
=======
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

>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
        busy = []
        for call in self.calls_for_carer_on_day(carer_id, day):
            call_start = _to_minutes(call.start_time)
            call_end = call_start + call.duration_minutes
            busy.append((call_start, call_end))
        busy.sort()

<<<<<<< HEAD
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
        """
        Scans all assignments and returns a list of (call_a, call_b, carer)
        tuples where the same carer has two assigned calls that overlap in
        time on a day they both apply to. Use this to catch double-bookings.

        NOTE: two DIFFERENT carers legitimately assigned to the SAME
        double-handed call is not a conflict — that's expected. This only
        flags when one carer is double-booked across two different calls.
        """
        conflicts = []
        by_carer = {}
        for a in self.assignments:
            by_carer.setdefault(a.carer_id, []).append(self.calls[a.call_id])

        for carer_id, calls in by_carer.items():
            for i in range(len(calls)):
                for j in range(i + 1, len(calls)):
                    call_a, call_b = calls[i], calls[j]
                    if call_a.call_id == call_b.call_id:
                        continue  # same call, different carer slot — not a conflict
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
        """
        Checks every carer's consecutive assigned calls on each day they
        occur, and flags any pair where the gap between the calls is
        shorter than the driving time between the two postcodes (plus an
        optional buffer, e.g. buffer_minutes=5 for a bit of slack).

        Returns a list of (call_a, call_b, carer, day, gap_minutes,
        travel_minutes) tuples for each problem pair.

        If a postcode lookup fails for a specific pair (e.g. missing/invalid
        postcode, API error), that pair is skipped and recorded separately
        in self.last_travel_check_errors instead of stopping the whole run.
        """
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
                        continue  # already flagged by find_conflicts (overlap)

                    postcode_a = self.clients[call_a.client_id].postcode
                    postcode_b = self.clients[call_b.client_id].postcode

                    try:
                        travel_minutes = get_travel_time_minutes(postcode_a, postcode_b)
                    except TravelTimeError as e:
                        errors.append((call_a, call_b, carer, day, str(e)))
                        continue

                    if gap_minutes < travel_minutes + buffer_minutes:
                        problems.append(
                            (call_a, call_b, carer, day, gap_minutes, travel_minutes)
                        )

        self.last_travel_check_errors = errors
        return problems

    def find_understaffed_calls(self) -> List[tuple]:
        """
        Returns a list of (call, required, assigned_count) tuples for any
        call where the number of DISTINCT carers assigned is less than
        call.carers_required (e.g. a double-handed call that only has 1
        carer assigned so far, or none at all).
        """
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
        """Returns True if any day of the week matches both patterns."""
        for day in DAY_ORDER:
            if day_matches_pattern(day, pattern_a) and day_matches_pattern(day, pattern_b):
                return True
        return False
=======
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
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c


# ---------------------------------------------------------------------------
# Demo / manual test when run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
<<<<<<< HEAD
    carers, availability = load_carers_and_availability("sample_data/carers.csv")
    clients, calls = load_clients_and_calls("sample_data/clients.csv")

    # Find Client 18's double-handed call (carers_required=2) to demo staffing.
    clients_by_id = {c.client_id: c for c in clients}
    client_18_calls = [c for c in calls if clients_by_id[c.client_id].full_name == "Client 18"]

    assignments = [
        Assignment(call_id=2, carer_id=8),   # Devi, Sunita -> Client 1, Mon 11:00-17:00
        Assignment(call_id=88, carer_id=8),  # Devi, Sunita -> Client 39, Mon 11:00-13:00 (overlaps call 2)
        Assignment(call_id=5, carer_id=8),   # Devi, Sunita -> Client 2, Mon-Sun 12:00-12:45 (overlaps both)
        Assignment(call_id=90, carer_id=7),  # Connelly, Angela -> Client 39, Thurs 16:30-17:00 (no conflict)
	Assignment(call_id=13, carer_id=8),  # Devi, Sunita -> Client 6, Mon-Sun 08:15-08:45 (BR8 7RA) — travel test
        Assignment(call_id=66, carer_id=8),  # Devi, Sunita -> Client 34, Mon-Sun 09:00-10:00 (DA1 2PU) — tight 15-min gap
    	]

    # Assign only ONE carer to Client 18's double-handed call, to show the
    # understaffed check catching it.
    if client_18_calls:
        assignments.append(Assignment(call_id=client_18_calls[0].call_id, carer_id=10))

    checker = CapacityChecker(clients, carers, availability, calls, assignments)

    print("=== Free slots for Adeyoluwa, Mary on Monday (overnight shift, real data) ===")
    for slot in checker.free_slots_for_carer(carer_id=2, day="Mon"):
        print(" ", slot)

    print()
    print("=== Free slots for Devi, Sunita on Monday (real assigned calls) ===")
    for slot in checker.free_slots_for_carer(carer_id=8, day="Mon"):
        print(" ", slot)

    print()
    print("=== Who is free Monday 10:00 for 30 minutes? ===")
    available = checker.find_available_carers(
        day="Mon", start_time=datetime.time(10, 0), duration_minutes=30
    )
    for carer, availability_type in available:
        print(f"  {carer.full_name} ({availability_type})")

    print()
    print("=== Checking for scheduling conflicts (real overlapping calls) ===")
    conflicts = checker.find_conflicts()
    if not conflicts:
        print("  No conflicts found.")
    else:
        for call_a, call_b, carer in conflicts:
            print(
                f"  CONFLICT: {carer.full_name} is assigned to overlapping calls "
                f"{call_a.call_id} ({call_a.start_time}-{call_a.duration_minutes}min) and "
                f"{call_b.call_id} ({call_b.start_time}-{call_b.duration_minutes}min)"
            )

    print()
    print("=== Checking for understaffed double-handed calls ===")
    understaffed = checker.find_understaffed_calls()
    if not understaffed:
        print("  All calls have enough carers assigned.")
    else:
        for call, required, assigned_count in understaffed:
            client_name = clients_by_id[call.client_id].full_name
            print(
                f"  Call {call.call_id} ({client_name}, {call.day_pattern} "
                f"{call.start_time}-needs {required} carers, only {assigned_count} assigned"
            )

    print()
    print("=== Checking for travel-time conflicts (real postcodes via Google Maps) ===")
    travel_conflicts = checker.find_travel_conflicts(buffer_minutes=5)
    if not travel_conflicts:
        print("  No travel-time conflicts found.")
    else:
        for call_a, call_b, carer, day, gap_minutes, travel_minutes in travel_conflicts:
            client_a = clients_by_id[call_a.client_id].full_name
            client_b = clients_by_id[call_b.client_id].full_name
            print(
                f"  {carer.full_name} on {day}: {client_a} ends "
                f"{call_a.start_time}+{call_a.duration_minutes}min, then {client_b} starts "
                f"{call_b.start_time} — only {gap_minutes} min gap, needs {travel_minutes} min travel"
            )

    if checker.last_travel_check_errors:
        print()
        print("=== Postcode/travel lookup errors (could not check these pairs) ===")
        for call_a, call_b, carer, day, error_message in checker.last_travel_check_errors:
            client_a = clients_by_id[call_a.client_id].full_name
            client_b = clients_by_id[call_b.client_id].full_name
            print(f"  {carer.full_name} on {day}: {client_a} -> {client_b}: {error_message}")
=======
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
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
