"""
Basic tests for capacity_checker.py

Run with:
    python -m unittest test_capacity_checker.py

No external test framework needed — uses Python's built-in unittest.
"""

import datetime
import unittest

from capacity_checker import (
    Assignment,
    Call,
    Carer,
    CapacityChecker,
    Client,
    day_matches_pattern,
)


class TestDayMatching(unittest.TestCase):
    def test_single_day(self):
        self.assertTrue(day_matches_pattern("Thurs", "Thurs"))
        self.assertFalse(day_matches_pattern("Fri", "Thurs"))

    def test_range(self):
        self.assertTrue(day_matches_pattern("Wed", "Mon-Sun"))
        self.assertTrue(day_matches_pattern("Sun", "Tues-Sun"))
        self.assertFalse(day_matches_pattern("Mon", "Tues-Sun"))

    def test_exclusion(self):
        self.assertFalse(day_matches_pattern("Tues", "Mon-Sun (minus Tues)"))
        self.assertTrue(day_matches_pattern("Wed", "Mon-Sun (minus Tues)"))


class TestCapacityChecker(unittest.TestCase):
    def setUp(self):
        self.clients = [Client(1, "Test Client", "AB1 2CD")]
        self.carers = [
            Carer(1, "Test Carer", datetime.time(7, 0), datetime.time(17, 0))
        ]
        self.calls = [
            Call(1, 1, "Mon-Sun", datetime.time(9, 0), datetime.time(9, 45), 45),
        ]
        self.assignments = [Assignment(call_id=1, carer_id=1)]
        self.checker = CapacityChecker(
            self.clients, self.carers, self.calls, self.assignments
        )

    def test_carer_busy_during_call(self):
        self.assertFalse(
            self.checker.is_carer_free(1, "Mon", datetime.time(9, 15), 15)
        )

    def test_carer_free_before_call(self):
        self.assertTrue(
            self.checker.is_carer_free(1, "Mon", datetime.time(7, 0), 30)
        )

    def test_carer_free_after_call(self):
        self.assertTrue(
            self.checker.is_carer_free(1, "Mon", datetime.time(10, 0), 60)
        )

    def test_outside_shift_hours(self):
        self.assertFalse(
            self.checker.is_carer_free(1, "Mon", datetime.time(18, 0), 30)
        )

    def test_free_slots(self):
        slots = self.checker.free_slots_for_carer(1, "Mon")
        self.assertEqual(slots, ["07:00-09:00", "09:45-17:00"])


if __name__ == "__main__":
    unittest.main()
