"""
Round generator — chains individual client calls into efficient rounds
based on postcode proximity and time, WITHOUT assigning carers.

Rules implemented:
  - Double-handed calls (carers_required=2) are duplicated into two
    identical parallel slots, each chained into a round independently.
  - Every call has +/-15 minutes of flexibility on its start time.
  - Max 20 minutes travel time allowed between consecutive calls in a
    round (a flat rule across the board).
  - No cap on how many calls can be chained into one round.
  - The algorithm always picks whichever feasible next call requires the
    SMALLEST time shift from its original start time — i.e. it minimises
    total drift from the times already on your system.
  - Shifts are suggestions only — original time and shifted time are both
    shown in the output so you can sanity-check before treating this as
    final.

How to run:
    python generate_rounds.py

Requires: capacity_checker.py and travel_time.py in the same folder,
and GOOGLE_MAPS_API_KEY set in the environment (see travel_time.py).
"""

from capacity_checker import (
    load_clients_and_calls,
    Call,
    DAY_ORDER,
    day_matches_pattern,
    _to_minutes,
    _normalise_day,
)

import datetime
from dataclasses import dataclass, replace
from typing import List, Optional

from capacity_checker import (
    load_clients_and_calls,
    Call,
    DAY_ORDER,
    day_matches_pattern,
    _to_minutes,
)
from travel_time import get_travel_time_minutes_with_source, TravelTimeError

import sys

_lookup_count = 0

def _progress(msg):
    print(msg, file=sys.stderr, flush=True)

MAX_SHIFT_MINUTES = 15
MAX_TRAVEL_MINUTES = 30
MAX_IDLE_MINUTES = 30  # gap ≥ this between calls ends the round

@dataclass
class RoundSlot:
    """
    One call placed into a round. Wraps the original Call plus the
    (possibly shifted) start time actually used in this round, and which
    duplicate index it is (for double-handed calls split into two slots).
    """
    call: Call
    slot_index: int          # 0 or 1 — which parallel slot, for double-handed calls
    day: str
    original_start_minutes: int
    scheduled_start_minutes: int

    @property
    def shift_minutes(self) -> int:
        return self.scheduled_start_minutes - self.original_start_minutes

    @property
    def scheduled_end_minutes(self) -> int:
        return self.scheduled_start_minutes + self.call.duration_minutes


def _fmt(minutes: int) -> str:
    minutes = minutes % (24 * 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _expand_calls_for_day(calls: List[Call], day: str, skipped_patterns: list, locked_starts: dict = None) -> List[RoundSlot]:
    """
    Returns one RoundSlot per call that occurs on `day`. If `locked_starts`
    contains an entry for a call_id (set after building the anchor day),
    that call's scheduled_start_minutes is forced to the locked value
    instead of its raw original start time, so recurring calls stay
    identical across every day they occur.
    """
    locked_starts = locked_starts or {}
    slots = []
    for call in calls:
        try:
            matches = day_matches_pattern(day, call.day_pattern)
        except ValueError as e:
            skipped_patterns.append((call, str(e)))
            continue
        if not matches:
            continue

        start_minutes = _to_minutes(call.start_time)
        locked_minutes = locked_starts.get(call.call_id)

        num_slots = max(call.carers_required, 1)
        for slot_index in range(num_slots):
            slots.append(
                RoundSlot(
                    call=call,
                    slot_index=slot_index,
                    day=day,
                    original_start_minutes=start_minutes,
                    scheduled_start_minutes=locked_minutes if locked_minutes is not None else start_minutes,
                )
            )
    return slots


_lookup_count = 0
_api_call_count = 0

def _travel_minutes_between(slot_a: RoundSlot, slot_b: RoundSlot, clients_by_id) -> Optional[int]:
    """Returns travel minutes between two slots' postcodes, or None if lookup fails."""
    global _lookup_count, _api_call_count
    postcode_a = clients_by_id[slot_a.call.client_id].postcode
    postcode_b = clients_by_id[slot_b.call.client_id].postcode
    try:
        result, was_cached = get_travel_time_minutes_with_source(postcode_a, postcode_b)
        _lookup_count += 1
        if not was_cached:
            _api_call_count += 1
        if _lookup_count % 200 == 0:
            _progress(f"  ...{_lookup_count} lookups so far ({_api_call_count} were real API calls, rest cached)")
        return result
    except TravelTimeError:
        return None

def build_rounds_for_day(calls: List[Call], day: str, clients_by_id, locked_starts: dict = None) -> tuple:
    """Anchor-day builder — full greedy chain, no template to replay yet."""
    locked_starts = locked_starts or {}
    skipped_patterns = []
    slots = _expand_calls_for_day(calls, day, skipped_patterns, locked_starts)
    slots.sort(key=lambda s: s.original_start_minutes)

    rounds = _greedy_chain_slots(slots, clients_by_id, locked_starts)
    rounds = _try_merge_rounds(rounds, clients_by_id)

    return rounds, [], skipped_patterns


def _try_merge_rounds(rounds: list, clients_by_id) -> list:
    """
    One pass over all rounds: if round B's first call can feasibly follow
    round A's last call (within travel/shift/idle limits), merge B into A.
    Repeats until no more merges are possible. Cuts down stray small
    rounds left behind by the forward-only greedy build.
    """
    merged_any = True
    while merged_any:
        merged_any = False
        for i in range(len(rounds)):
            if rounds[i] is None:
                continue
            last = rounds[i][-1]
            for j in range(len(rounds)):
                if i == j or rounds[j] is None:
                    continue
                first = rounds[j][0]

                travel = _travel_minutes_between(last, first, clients_by_id)
                if travel is None or travel > MAX_TRAVEL_MINUTES:
                    continue

                earliest_possible_start = last.scheduled_end_minutes + travel
                min_allowed = first.original_start_minutes - MAX_SHIFT_MINUTES
                max_allowed = first.original_start_minutes + MAX_SHIFT_MINUTES
                new_start = max(earliest_possible_start, min_allowed)
                if new_start > max_allowed:
                    continue

                idle_gap = new_start - last.scheduled_end_minutes - travel
                if idle_gap >= MAX_IDLE_MINUTES:
                    continue

                # Feasible merge: shift round j's start and re-derive the
                # rest of its internal timings by the same delta.
                delta = new_start - first.scheduled_start_minutes
                for slot in rounds[j]:
                    slot.scheduled_start_minutes += delta

                rounds[i] = rounds[i] + rounds[j]
                rounds[j] = None
                merged_any = True
                break
            if merged_any:
                break

    return [r for r in rounds if r is not None]

def _is_recurring_call(call: Call) -> bool:
    """A call is 'recurring' if its day_pattern matches more than one day
    of the week — these get their time locked after the first day they're
    built, so they never drift day-to-day."""
    matching_days = [d for d in DAY_ORDER if day_matches_pattern(d, call.day_pattern)]
    return len(matching_days) > 1



def _split_round_at_cutoff(round_slots, cutoff_minutes=17 * 60 + 30):
    """
    Splits one round's calls into an early portion and a late portion at
    the cutoff time. A call that straddles the cutoff (starts before,
    ends after) is kept whole and placed in the late portion, since it
    finishes late.
    """
    early_part = []
    late_part = []
    in_late = False
    for slot in round_slots:
        if not in_late and slot.scheduled_start_minutes < cutoff_minutes and slot.scheduled_end_minutes <= cutoff_minutes:
            early_part.append(slot)
        else:
            in_late = True
            late_part.append(slot)
    return early_part, late_part


def _print_round_slots(label, round_slots, clients_by_id):
    total_travel = 0
    for a, b in zip(round_slots, round_slots[1:]):
        travel = _travel_minutes_between(a, b, clients_by_id)
        total_travel += travel or 0

    print(f"\n=== {label} ({len(round_slots)} calls, total travel: {total_travel} min) ===")
    for slot in round_slots:
        client_name = clients_by_id[slot.call.client_id].full_name
        postcode = clients_by_id[slot.call.client_id].postcode
        if slot.shift_minutes != 0:
            direction = "later" if slot.shift_minutes > 0 else "earlier"
            shift_note = f"  [original {_fmt(slot.original_start_minutes)} — shifted {abs(slot.shift_minutes)} min {direction}]"
        else:
            shift_note = f"  [original {_fmt(slot.original_start_minutes)} — no shift]"
        dup_note = f" (slot {slot.slot_index + 1} of {slot.call.carers_required})" if slot.call.carers_required > 1 else ""

        print(
            f"  {_fmt(slot.scheduled_start_minutes)}-{_fmt(slot.scheduled_end_minutes)}  "
            f"{client_name}{dup_note}   ({postcode}){shift_note}"
        )


def print_rounds(rounds, day, clients_by_id):
    early_entries = []   # list of (round_number, round_slots)
    late_entries = []    # list of (round_number, round_slots, is_continuation)

    for round_number, round_slots in enumerate(rounds, start=1):
        early_part, late_part = _split_round_at_cutoff(round_slots)

        if early_part:
            early_entries.append((round_number, early_part))
        if late_part:
            is_continuation = bool(early_part)
            late_entries.append((round_number, late_part, is_continuation))

    print(f"\n########## EARLY ({day}) — {len(early_entries)} rounds ##########")
    for round_number, slots in early_entries:
        _print_round_slots(f"EARLY Round {round_number} — {day}", slots, clients_by_id)

    print(f"\n########## LATE ({day}) — {len(late_entries)} rounds ##########")
    for round_number, slots, is_continuation in late_entries:
        tag = f"LATE Round {round_number} (continued) — {day}" if is_continuation else f"LATE Round {round_number} — {day}"
        _print_round_slots(tag, slots, clients_by_id)

import csv

def export_rounds_to_csv(rounds, day, clients_by_id, output_path=None):
    """
    Exports all rounds for a day to a CSV file, one row per call-slot.
    Splits rounds at the same 17:30 cutoff used for the EARLY/LATE display,
    so the CSV matches what you see in the terminal output.
    """
    if output_path is None:
        output_path = f"rounds_{day}.csv"

    rows = []

    for round_number, round_slots in enumerate(rounds, start=1):
        early_part, late_part = _split_round_at_cutoff(round_slots)

        if early_part:
            _append_csv_rows(rows, day, "EARLY", round_number, False, early_part, clients_by_id)
        if late_part:
            is_continuation = bool(early_part)
            _append_csv_rows(rows, day, "LATE", round_number, is_continuation, late_part, clients_by_id)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Day", "Section", "Round Number", "Continued From Early",
            "Scheduled Start", "Scheduled End", "Client Name", "Slot Info",
            "Postcode", "Original Start", "Shift (min)", "Shift Note",
        ])
        writer.writerows(rows)

    print(f"  Exported {len(rows)} call-slot rows to {output_path}")
    return output_path

def _build_templates(anchor_rounds: list) -> list:
    """
    Converts Monday's built rounds into templates — the ordered list of
    unique call_ids in each round. Deduplication happens ACROSS THE WHOLE
    DAY, not just within a single round, because a double-handed call's
    two slots can occasionally end up split across two different rounds
    on the anchor day (e.g. Client 65). Without a day-wide dedupe, that
    call_id would appear in two separate templates and get expanded back
    into slots twice on replay days, causing duplicates.
    """
    templates = []
    seen_today = set()
    for round_slots in anchor_rounds:
        call_ids = []
        for slot in round_slots:
            if slot.call.call_id not in seen_today:
                seen_today.add(slot.call.call_id)
                call_ids.append(slot.call.call_id)
        templates.append(call_ids)
    return templates

def _replay_template(template_call_ids: list, day: str, calls_by_id: dict, locked_starts: dict) -> list:
    """
    Walks a Monday template in its fixed order. Any call that doesn't
    happen on `day` is simply skipped (a gap) — it does NOT trigger
    picking a different call to fill its place. Calls that do occur keep
    their locked time from the anchor day, so the round's shape and
    timing stay identical to Monday wherever possible.
    """
    round_slots = []
    for call_id in template_call_ids:
        call = calls_by_id.get(call_id)
        if call is None:
            continue
        if not day_matches_pattern(day, call.day_pattern):
            continue  # gap — this call isn't on today, leave it out, move on

        start_minutes = locked_starts.get(call_id, _to_minutes(call.start_time))
        num_slots = max(call.carers_required, 1)
        for slot_index in range(num_slots):
            round_slots.append(
                RoundSlot(
                    call=call,
                    slot_index=slot_index,
                    day=day,
                    original_start_minutes=_to_minutes(call.start_time),
                    scheduled_start_minutes=start_minutes,
                )
            )
    return round_slots

def _try_insert_leftover_into_round(round_slots: list, leftover_slot, clients_by_id) -> bool:
    """
    Tries to insert `leftover_slot` somewhere into an existing (already
    time-locked) round without disturbing any locked call's time. Only
    succeeds if it fits cleanly into a genuine gap — travel there, travel
    away, and the idle gap all within the normal limits. Returns True and
    mutates round_slots in place if it fits; False otherwise.
    """
    if not round_slots:
        return False

    for i in range(len(round_slots) + 1):
        prev_slot = round_slots[i - 1] if i > 0 else None
        next_slot = round_slots[i] if i < len(round_slots) else None

        # Work out earliest arrival after prev_slot (or the call's own
        # flexibility window if it's being inserted at the very start).
        if prev_slot is not None:
            travel_in = _travel_minutes_between(prev_slot, leftover_slot, clients_by_id)
            if travel_in is None or travel_in > MAX_TRAVEL_MINUTES:
                continue
            earliest_start = prev_slot.scheduled_end_minutes + travel_in
        else:
            earliest_start = leftover_slot.original_start_minutes - MAX_SHIFT_MINUTES

        min_allowed = leftover_slot.original_start_minutes - MAX_SHIFT_MINUTES
        max_allowed = leftover_slot.original_start_minutes + MAX_SHIFT_MINUTES
        new_start = max(earliest_start, min_allowed)
        if new_start > max_allowed:
            continue

        if prev_slot is not None:
            idle_gap = new_start - prev_slot.scheduled_end_minutes - travel_in
            if idle_gap >= MAX_IDLE_MINUTES:
                continue

        candidate_end = new_start + leftover_slot.call.duration_minutes

        # Must also fit before next_slot without disturbing its LOCKED time.
        if next_slot is not None:
            travel_out = _travel_minutes_between(leftover_slot, next_slot, clients_by_id)
            if travel_out is None or travel_out > MAX_TRAVEL_MINUTES:
                continue
            if candidate_end + travel_out > next_slot.scheduled_start_minutes:
                continue  # would push into the next locked call — reject

        leftover_slot.scheduled_start_minutes = new_start
        round_slots.insert(i, leftover_slot)
        return True

    return False

def build_rounds_for_day_from_templates(
    calls: List[Call], day: str, clients_by_id, templates: list, locked_starts: dict
) -> tuple:
    """
    For non-anchor days: replay each Monday template (keeping shape/times
    fixed, skipping gaps), then try to fit any leftover day-specific calls
    into those gaps. Anything that still doesn't fit anywhere falls back
    to the normal greedy chain-builder to form brand-new rounds.
    """
    calls_by_id = {c.call_id: c for c in calls}
    skipped_patterns = []

    # Which calls happen today at all?
    todays_call_ids = set()
    for call in calls:
        try:
            if day_matches_pattern(day, call.day_pattern):
                todays_call_ids.add(call.call_id)
        except ValueError as e:
            skipped_patterns.append((call, str(e)))

    # Replay every template.
    replayed_rounds = []
    consumed_call_ids = set()
    for template_call_ids in templates:
        round_slots = _replay_template(template_call_ids, day, calls_by_id, locked_starts)
        if round_slots:
            replayed_rounds.append(round_slots)
            for slot in round_slots:
                consumed_call_ids.add(slot.call.call_id)

    # Everything happening today that wasn't part of any template.
    leftover_call_ids = todays_call_ids - consumed_call_ids
    leftover_slots = []
    for call_id in leftover_call_ids:
        call = calls_by_id[call_id]
        start_minutes = _to_minutes(call.start_time)
        num_slots = max(call.carers_required, 1)
        for slot_index in range(num_slots):
            leftover_slots.append(
                RoundSlot(
                    call=call, slot_index=slot_index, day=day,
                    original_start_minutes=start_minutes,
                    scheduled_start_minutes=start_minutes,
                )
            )
    leftover_slots.sort(key=lambda s: s.original_start_minutes)

    # Try to squeeze each leftover into an existing replayed round's gaps first.
    still_unplaced = []
    for leftover_slot in leftover_slots:
        placed = False
        for round_slots in replayed_rounds:
            if _try_insert_leftover_into_round(round_slots, leftover_slot, clients_by_id):
                placed = True
                break
        if not placed:
            still_unplaced.append(leftover_slot)

    # Anything that still doesn't fit gets chained into brand-new rounds
    # using the normal greedy builder (unchanged behaviour, just scoped to
    # only the genuinely-unplaced calls).
    extra_rounds = []
    if still_unplaced:
        extra_rounds = _greedy_chain_slots(still_unplaced, clients_by_id)

    all_rounds = replayed_rounds + extra_rounds
    all_rounds = _try_merge_rounds(all_rounds, clients_by_id)

    return all_rounds, [], skipped_patterns

def _greedy_chain_slots(slots: list, clients_by_id, locked_starts: dict = None) -> list:
    """
    The original greedy chain-builder, extracted so it can be reused both
    for the anchor day (Monday) and for leftover calls on later days.
    """
    locked_starts = locked_starts or {}
    unassigned = list(slots)
    rounds = []

    while unassigned:
        current = unassigned.pop(0)
        current_round = [current]

        while True:
            best_candidate = None
            best_candidate_index = None
            best_shift_abs = None
            best_new_start = None
            best_travel = None

            last = current_round[-1]

            window_start = last.scheduled_end_minutes - MAX_SHIFT_MINUTES
            window_end = last.scheduled_end_minutes + MAX_TRAVEL_MINUTES + MAX_IDLE_MINUTES + MAX_SHIFT_MINUTES

            plausible_candidates = [
                (idx, c) for idx, c in enumerate(unassigned)
                if window_start <= c.original_start_minutes <= window_end
                or c.call.call_id in locked_starts
            ]

            for idx, candidate in plausible_candidates:
                travel = _travel_minutes_between(last, candidate, clients_by_id)
                if travel is None or travel > MAX_TRAVEL_MINUTES:
                    continue

                is_locked = candidate.call.call_id in locked_starts
                if is_locked:
                    new_start = locked_starts[candidate.call.call_id]
                    earliest_possible_start = last.scheduled_end_minutes + travel
                    if earliest_possible_start > new_start:
                        continue
                else:
                    earliest_possible_start = last.scheduled_end_minutes + travel
                    min_allowed = candidate.original_start_minutes - MAX_SHIFT_MINUTES
                    max_allowed = candidate.original_start_minutes + MAX_SHIFT_MINUTES
                    new_start = max(earliest_possible_start, min_allowed)
                    if new_start > max_allowed:
                        continue

                idle_gap = new_start - last.scheduled_end_minutes - travel
                if idle_gap >= MAX_IDLE_MINUTES:
                    continue

                shift_abs = abs(new_start - candidate.original_start_minutes)
                is_better = (
                    best_travel is None
                    or travel < best_travel
                    or (travel == best_travel and shift_abs < best_shift_abs)
                )
                if is_better:
                    best_travel = travel
                    best_shift_abs = shift_abs
                    best_candidate = candidate
                    best_candidate_index = idx
                    best_new_start = new_start

            if best_candidate is None:
                break

            best_candidate.scheduled_start_minutes = best_new_start
            current_round.append(best_candidate)
            unassigned.pop(best_candidate_index)

            if best_candidate.call.carers_required > 1:
                twin = next(
                    (s for s in unassigned
                     if s.call.client_id == best_candidate.call.client_id
                     and s.call.start_time == best_candidate.call.start_time
                     and s.slot_index != best_candidate.slot_index),
                    None
                )
                if twin is not None:
                    twin.scheduled_start_minutes = best_candidate.scheduled_start_minutes
                    unassigned.remove(twin)
                    current_round.append(twin)

        rounds.append(current_round)

    return rounds

def _append_csv_rows(rows, day, section, round_number, is_continuation, slots, clients_by_id):
    for slot in slots:
        client = clients_by_id[slot.call.client_id]
        slot_info = f"slot {slot.slot_index + 1} of {slot.call.carers_required}" if slot.call.carers_required > 1 else ""
        if slot.shift_minutes != 0:
            direction = "later" if slot.shift_minutes > 0 else "earlier"
            shift_note = f"shifted {abs(slot.shift_minutes)} min {direction}"
        else:
            shift_note = "no shift"

        rows.append([
            day,
            section,
            round_number,
            "Yes" if is_continuation else "No",
            _fmt(slot.scheduled_start_minutes),
            _fmt(slot.scheduled_end_minutes),
            client.full_name,
            slot_info,
            client.postcode,
            _fmt(slot.original_start_minutes),
            slot.shift_minutes,
            shift_note,
        ])

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate efficient rounds from client calls.")
    parser.add_argument("--day", help="Only process a single day, e.g. Mon, Tues, Wed", default=None)
    parser.add_argument("--limit", type=int, help="Only use the first N calls (for quick testing)", default=None)
    args = parser.parse_args()

    clients, calls = load_clients_and_calls("sample_data/clients.csv")
    clients_by_id = {c.client_id: c for c in clients}

    if args.limit:
        calls = calls[:args.limit]
        _progress(f"(testing mode: limited to first {len(calls)} calls)")

    days_to_process = [_normalise_day(args.day)] if args.day else DAY_ORDER

    grand_total_calls = 0
    grand_total_rounds = 0
    locked_starts = {}
    templates = []

    for day_index, day in enumerate(days_to_process):
        _progress(f"\nProcessing {day}...")

        if day_index == 0:
            rounds, unplaced_errors, skipped_patterns = build_rounds_for_day(
                calls, day, clients_by_id, locked_starts
            )
            for round_slots in rounds:
                for slot in round_slots:
                    if _is_recurring_call(slot.call) and slot.call.call_id not in locked_starts:
                        locked_starts[slot.call.call_id] = slot.scheduled_start_minutes
            templates = _build_templates(rounds)
        else:
            rounds, unplaced_errors, skipped_patterns = build_rounds_for_day_from_templates(
                calls, day, clients_by_id, templates, locked_starts
            )

        if not rounds and not skipped_patterns:
            continue

        if rounds:
            print_rounds(rounds, day, clients_by_id)
            export_rounds_to_csv(rounds, day, clients_by_id)

        if unplaced_errors:
            print(f"\n--- Postcode lookup issues on {day} ---")
            for slot, reason in unplaced_errors:
                client_name = clients_by_id[slot.call.client_id].full_name
                print(f"  {client_name}: {reason}")

        if skipped_patterns:
            print(f"\n--- Unrecognised day patterns on {day} (skipped, needs manual review) ---")
            for call, reason in skipped_patterns:
                client_name = clients_by_id[call.client_id].full_name
                print(f"  {client_name}: '{call.day_pattern}' — {reason}")

        day_call_count = sum(len(r) for r in rounds)
        grand_total_calls += day_call_count
        grand_total_rounds += len(rounds)

        print(f"\n--- {day} summary: {day_call_count} call-slots across {len(rounds)} rounds ---")
	
    print(f"  Real Google Maps API calls made this run: {_api_call_count}")

    print("\n=== Overall summary ===")
    print(f"  Total call-slots placed: {grand_total_calls}")
    print(f"  Total rounds generated: {grand_total_rounds}")