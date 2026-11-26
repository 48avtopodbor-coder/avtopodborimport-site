from datetime import date
import importlib.util
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


COLLECTOR = Path(__file__).resolve().parents[1] / "scripts" / "collector"
with patch.object(sys, "path", [str(COLLECTOR), *sys.path]):
    from registration_age import customs_registration_bounds, customs_years, in_customs_window, registration_month


class RegistrationAgeTests(unittest.TestCase):
    def test_registration_formats(self):
        for value in (" 2023-04 ", "2023-4-30", "2023/04/05", "2023.4", "2023年4月", "2023年4月5日", "05.04.2023"):
            with self.subTest(value=value):
                self.assertEqual(registration_month(value, 2020), date(2023, 4, 1))

    def test_missing_invalid_and_leap_dates(self):
        for value in (None, "", "2023", "2023-02-29", "2023-13", "2023-04/05", "0000-01", "unknown"):
            with self.subTest(value=value):
                self.assertEqual(registration_month(value, "2022"), date(2022, 7, 1))
        self.assertEqual(registration_month("2024-02-29", 2020), date(2024, 2, 1))
        self.assertIsNone(registration_month(None, None))

    def test_window_uses_delivery_date_across_year_end(self):
        for today, day in ((date(2026, 11, 26), (1, 10)), (date(2026, 12, 20), (2, 3))):
            with self.subTest(today=today):
                self.assertEqual(customs_years(today), (2022, 2024))
                self.assertEqual(customs_registration_bounds(today), (date(2022, *day), date(2024, *day)))
        self.assertEqual(
            customs_registration_bounds(date(2024, 1, 15)),
            (date(2019, 2, 28), date(2021, 2, 28)),
        )

    def test_window_requires_the_entire_registration_month(self):
        for today, january_allowed in (
            (date(2026, 11, 26), False),
            (date(2026, 12, 16), False),
            (date(2026, 12, 17), True),
        ):
            with self.subTest(today=today):
                self.assertFalse(in_customs_window(date(2022, 1, 1), today))
                self.assertTrue(in_customs_window(date(2022, 2, 1), today))
                self.assertTrue(in_customs_window(date(2023, 12, 1), today))
                self.assertEqual(in_customs_window(date(2024, 1, 1), today), january_allowed)
                self.assertFalse(in_customs_window(date(2024, 2, 1), today))
                self.assertFalse(in_customs_window(None, today))
        # The earliest bound is exclusive even if the cutoff is the first of a month.
        self.assertFalse(in_customs_window(date(2022, 1, 1), date(2026, 11, 17)))

    def test_recheck_keeps_only_candidates_that_could_still_be_eligible(self):
        spec = importlib.util.spec_from_file_location("enrich_for_age_test", COLLECTOR / "enrich.py")
        enrich = importlib.util.module_from_spec(spec)
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE cars (listing_id TEXT, first_reg_date TEXT, year INTEGER, "
                       "is_active INTEGER, enriched_at TEXT, updated_at TEXT)")
            rows = [
                ("old", "2021-12", 2021),
                ("boundary", "2022-01", 2022),
                ("fallback-old", None, 2021),
                ("fallback-ok", "", 2022),
                ("youngest-boundary", "2024-01", 2024),
                ("too-young-for-now", "2025-01", 2025),
                ("unknown", None, None),
            ]
            db.executemany("INSERT INTO cars VALUES (?, ?, ?, 1, 'set', ?)", [
                (*row, f"2000-01-{i:02}") for i, row in enumerate(rows, 1)
            ])
            database = SimpleNamespace(init_db=Mock(), cars_to_enrich=Mock(),
                                       update_details=Mock(), get_conn=lambda: db)
            with patch.object(sys, "path", [str(COLLECTOR), *sys.path]), patch.dict(
                sys.modules, {"database": database, "loguru": SimpleNamespace(logger=Mock())}
            ):
                spec.loader.exec_module(enrich)
            oldest, youngest = customs_registration_bounds(date(2026, 11, 17))
            with patch.object(enrich, "customs_registration_bounds", return_value=(oldest, youngest)), patch.object(
                enrich, "process"
            ) as process:
                enrich.recheck_active()
                self.assertEqual(process.call_args.args[0], ["fallback-ok", "youngest-boundary", "too-young-for-now", "unknown"])
                enrich.recheck_active(limit=2)
                self.assertEqual(process.call_args.args[0], ["fallback-ok", "youngest-boundary"])
