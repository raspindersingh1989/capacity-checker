"""
Basic tests for capacity_checker.py

Run with:
    python -m unittest test_capacity_checker.py
<<<<<<< HEAD
=======

No external test framework needed — uses Python's built-in unittest.
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
"""

import datetime
import unittest

from capacity_checker import (
    Assignment,
    Call,
    Carer,
<<<<<<< HEAD
    CarerAvailability,
=======
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
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
<<<<<<< HEAD
        self.assertFalse(day_matches_pattern("Sat", "Mon-Sun (minus Sat)"))
        self.assertTrue(day_matches_pattern("Fri", "Mon-Sun (minus Sat)"))
=======
        self.assertFalse(day_matches_pattern("Tues", "Mon-Sun (minus Tues)"))
        self.assertTrue(day_matches_pattern("Wed", "Mon-Sun (minus Tues)"))
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c


class TestCapacityChecker(unittest.TestCase):
    def setUp(self):
        self.clients = [Client(1, "Test Client", "AB1 2CD")]
<<<<<<< HEAD
        self.carers = [Carer(1, "Test Carer")]
        self.availability = [
            CarerAvailability(1, "Mon-Sun", datetime.time(9, 0), datetime.time(12, 0), "core"),
            CarerAvailability(1, "Mon-Sun", datetime.time(13, 0), datetime.time(14, 0), "optional"),
            CarerAvailability(1, "Mon-Sun", datetime.time(16, 0), datetime.time(18, 0), "optional"),
        ]
        self.calls = [
            Call(1, 1, 1, "Mon-Sun", datetime.time(9, 0), datetime.time(9, 45), 45),
        ]
        self.assignments = [Assignment(call_id=1, carer_id=1)]
        self.checker = CapacityChecker(
            self.clients, self.carers, self.availability, self.calls, self.assignments
        )

    def test_core_slot_available(self):
        self.assertEqual(
            self.checker.check_carer_slot(1, "Mon", datetime.time(10, 0), 60), "core"
        )

    def test_optional_slot_available(self):
        self.assertEqual(
            self.checker.check_carer_slot(1, "Mon", datetime.time(13, 0), 30), "optional"
        )

    def test_gap_between_windows_not_available(self):
        self.assertIsNone(
            self.checker.check_carer_slot(1, "Mon", datetime.time(12, 15), 15)
        )

    def test_busy_during_call(self):
        self.assertIsNone(
            self.checker.check_carer_slot(1, "Mon", datetime.time(9, 15), 15)
        )

    def test_outside_any_window(self):
        self.assertIsNone(
            self.checker.check_carer_slot(1, "Mon", datetime.time(19, 0), 30)
        )

    def test_free_slots_labelled(self):
        slots = self.checker.free_slots_for_carer(1, "Mon")
        self.assertIn("09:45-12:00 (core)", slots)
        self.assertIn("13:00-14:00 (optional)", slots)
        self.assertIn("16:00-18:00 (optional)", slots)


class TestDaysOff(unittest.TestCase):
    def setUp(self):
        self.clients = []
        self.carers = [Carer(2, "No Sat Carer")]
        self.availability = [
            CarerAvailability(2, "Mon-Sun (minus Sat)", datetime.time(9, 0), datetime.time(17, 0), "core"),
        ]
        self.calls = []
        self.assignments = []
        self.checker = CapacityChecker(
            self.clients, self.carers, self.availability, self.calls, self.assignments
        )

    def test_working_day(self):
        self.assertEqual(
            self.checker.check_carer_slot(2, "Fri", datetime.time(10, 0), 30), "core"
        )

    def test_day_off(self):
        self.assertIsNone(
            self.checker.check_carer_slot(2, "Sat", datetime.time(10, 0), 30)
        )


class TestOvernightShift(unittest.TestCase):
    def setUp(self):
        self.clients = []
        self.carers = [Carer(3, "Night Carer")]
        # 22:00 Monday to 06:00 Tuesday
        self.availability = [
            CarerAvailability(3, "Mon-Sun", datetime.time(22, 0), datetime.time(6, 0), "core"),
        ]
        self.calls = []
        self.assignments = []
        self.checker = CapacityChecker(
            self.clients, self.carers, self.availability, self.calls, self.assignments
        )

    def test_late_monday_night(self):
        # 23:00 Monday should be covered by the Monday-starting window
        self.assertEqual(
            self.checker.check_carer_slot(3, "Mon", datetime.time(23, 0), 60), "core"
        )

    def test_early_tuesday_morning(self):
        # 03:00 Tuesday should ALSO be covered, because the window spans midnight
        self.assertEqual(
            self.checker.check_carer_slot(3, "Tues", datetime.time(3, 0), 60), "core"
        )

    def test_daytime_not_covered(self):
        self.assertIsNone(
            self.checker.check_carer_slot(3, "Mon", datetime.time(12, 0), 30)
        )

    def test_free_slots_for_overnight(self):
        slots = self.checker.free_slots_for_carer(3, "Tues")
        # Should show the tail end of Monday's overnight window as free on Tuesday
        self.assertIn("00:00-06:00 (core)", slots)


if __name__ == "__main__":
    unittest.main()
=======
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
>>>>>>> f3ebba744c78b2dfdb5d8ad39f7f2ace9dc39b0c
