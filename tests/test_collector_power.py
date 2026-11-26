from contextlib import closing, redirect_stdout
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


COLLECTOR = Path(__file__).resolve().parents[1] / "scripts" / "collector"
FIXTURES = json.loads((Path(__file__).parent / "fixtures/electrified-power.json").read_text(encoding="utf-8"))


class CollectorPowerTests(unittest.TestCase):
    def test_power_fields_and_primary_figure_from_real_specs(self):
        with patch.object(sys, "path", [str(COLLECTOR), *sys.path]):
            from power import electrified_power_hp, spec_power

        for entry in FIXTURES:
            with self.subTest(spec_id=entry["spec_id"]):
                raw = json.dumps(entry["params_json"], ensure_ascii=False)
                self.assertEqual(spec_power(raw), {key: entry[key] for key in ("engine_hp", "motor_hp", "total_hp")})
                self.assertEqual(electrified_power_hp(raw, entry["fuel"]), entry["primary_hp"])

    def test_backfill_reports_and_applies_both_tables_without_api(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "cars.db"
            with closing(sqlite3.connect(database)) as con, con:
                con.execute("CREATE TABLE specs(spec_id TEXT PRIMARY KEY, fuel TEXT, params_json TEXT, power_hp INTEGER)")
                con.execute("CREATE TABLE cars(spec_id TEXT, power_hp INTEGER, is_active INTEGER, price_cny INTEGER)")
                con.executemany("INSERT INTO specs VALUES (?, ?, ?, ?)", [
                    (row["spec_id"], row["fuel"], json.dumps(row["params_json"]), hp)
                    for row, hp in zip(FIXTURES[:2], (131, 408))
                ])
                con.executemany("INSERT INTO cars VALUES (?, ?, ?, 50000)", [
                    ("42429", 131, 1), ("60970", 252, 1), ("42429", None, 0), ("other", 100, 1),
                ])
            with patch.object(sys, "path", [str(COLLECTOR), *sys.path]), patch.dict(
                sys.modules, {"config": SimpleNamespace(DB_PATH=str(database))}
            ):
                import backfill_power

            with patch.object(backfill_power, "DB_PATH", str(database)):
                for flags, expected, saved in (
                    ([], (1, 3, 2), [131, 252, None, 100]),
                    (["--apply"], (1, 3, 2), [326, 408, 326, 100]),
                    (["--apply"], (0, 0, 0), [326, 408, 326, 100]),
                ):
                    output = io.StringIO()
                    with patch.object(sys, "argv", ["backfill_power.py", *flags]), redirect_stdout(output):
                        backfill_power.main()
                    report = json.loads(output.getvalue())
                    self.assertEqual(tuple(report[key] for key in ("specs", "cars", "active_cards")), expected)
                    with closing(sqlite3.connect(database)) as con:
                        self.assertEqual([row[0] for row in con.execute("SELECT power_hp FROM cars ORDER BY rowid")], saved)
                        spec_hp = con.execute("SELECT power_hp FROM specs WHERE spec_id='42429'").fetchone()[0]
                        self.assertEqual(spec_hp, saved[0])
