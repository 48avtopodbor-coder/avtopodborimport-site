import importlib.util
from contextlib import redirect_stdout
import io
import json
import os
from collections import Counter
from datetime import date
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch


spec = importlib.util.spec_from_file_location(
    "import_cars", Path(__file__).resolve().parents[1] / "scripts" / "import_cars.py"
)
import_cars = importlib.util.module_from_spec(spec)
spec.loader.exec_module(import_cars)


def create_database(path):
    with sqlite3.connect(path) as connection:
        for name, columns in (("cars", import_cars.CAR_COLS), ("specs", import_cars.SPEC_SRC)):
            fields = ", ".join(f'"{column}" TEXT' for column in columns)
            connection.execute(f"CREATE TABLE {name} ({fields})")


class SnapshotTests(unittest.TestCase):
    def test_import_derives_registration_month_without_a_brand_mapping(self):
        for first_reg_date, expected in (("2023/03/17", date(2023, 3, 1)), ("", date(2022, 7, 1))):
            with self.subTest(first_reg_date=first_reg_date):
                row = {"listing_id": "123", "year": 2022, "first_reg_date": first_reg_date}
                source = tuple(row.get(column) for column in import_cars.CAR_COLS)
                imported = dict(zip(
                    import_cars.CAR_DST_COLS,
                    import_cars.enrich_car(source, {}, {}, Counter()),
                    strict=True,
                ))
                self.assertEqual(imported["reg_month"], expected)

    def test_import_wraps_legacy_cover_without_overwriting_detail_photos(self):
        cover = "https://2sc2.autoimg.cn/cars/cover.webp"
        gallery = '["https://2sc2.autoimg.cn/cars/detail.webp"]'
        for images, expected in (
            (cover, json.dumps([cover])),
            (gallery, gallery),
            (None, None),
            ("https://other.example/cars/cover.webp", "https://other.example/cars/cover.webp"),
        ):
            with self.subTest(images=images):
                row = {"listing_id": "123", "images": images, "photos": gallery}
                source = tuple(row.get(column) for column in import_cars.CAR_COLS)
                imported = dict(zip(
                    import_cars.CAR_DST_COLS,
                    import_cars.enrich_car(source, {}, {}, Counter()),
                ))
                self.assertEqual(imported["images"], expected)
                self.assertEqual(imported["photos"], gallery)

    def test_hard_link_and_published_path_share_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            published = Path(directory) / "cars.db"
            snapshot = Path(directory) / "snapshot.db"
            create_database(published)
            os.link(published, snapshot)
            with patch.object(import_cars, "SQLITE_PATH", str(snapshot)):
                connection, _, snapshot_identity = import_cars.open_source(published=True)
                connection.close()
            with patch.object(import_cars, "SQLITE_PATH", str(published)):
                connection, _, published_identity = import_cars.open_source(published=True)
                connection.close()
            self.assertEqual(snapshot_identity, published_identity)

    def test_replacement_during_open_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            published = Path(directory) / "cars.db"
            replacement = Path(directory) / "replacement.db"
            create_database(published)
            create_database(replacement)
            real_connect = sqlite3.connect

            def replace_after_open(*args, **kwargs):
                connection = real_connect(*args, **kwargs)
                os.replace(replacement, published)
                return connection

            with patch.object(import_cars, "SQLITE_PATH", str(published)), patch.object(
                import_cars.sqlite3, "connect", side_effect=replace_after_open
            ):
                with self.assertRaisesRegex(SystemExit, "изменилась во время открытия"):
                    import_cars.open_source(published=True)

    def test_regular_import_keeps_age_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            published = Path(directory) / "cars.db"
            create_database(published)
            with patch.object(import_cars, "SQLITE_PATH", str(published)):
                with self.assertRaisesRegex(SystemExit, "возможно, ещё пишется"):
                    import_cars.open_source()

    def test_age_cleanup_uses_exclusive_old_boundary_and_preserves_corrected_and_young_cars(self):
        with sqlite3.connect(":memory:") as source:
            source.execute("CREATE TABLE cars(listing_id text, first_reg_date text, year integer, is_active integer)")
            source.executemany("INSERT INTO cars VALUES (?, ?, ?, 1)", [
                ("exact", "2022-01", 2022),
                ("eligible", "2022-02", 2022),
                ("young", "2024-02", 2024),
                ("corrected", "2022-03", 2022),
                ("cached-old", None, None),
                ("source-old", "2021-12", 2021),
            ])
            cursor = MagicMock()
            cursor.fetchone.return_value = (date(2026, 11, 17),)
            cursor.__iter__.return_value = iter([
                ("exact", date(2022, 1, 1), "2022-01", 2022),
                ("eligible", date(2022, 2, 1), "2022-02", 2022),
                ("young", date(2024, 2, 1), "2024-02", 2024),
                ("corrected", date(2021, 12, 1), "2021-12", 2021),
                ("cached-old", date(2021, 11, 1), "2021-11", 2021),
                ("source-old", date(2023, 11, 1), "2023-11", 2023),
                ("site-only", date(2021, 10, 1), "2021-10", 2021),
            ])
            oldest, excluded, aged = import_cars.registration_cleanup_plan(source, cursor)
        self.assertEqual(oldest, date(2022, 1, 1))
        self.assertEqual(excluded, {"exact", "source-old"})
        self.assertEqual(aged, {"exact", "cached-old", "source-old", "site-only"})


    def test_blocked_deletion_commits_import_and_manual_flag_reuses_same_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "last_import"
            lock = Path(directory) / "import.lock"
            sq = Mock()
            sq.execute.return_value.fetchone.side_effect = [(50, 40), (10,)] * 3
            pg = MagicMock()
            pg.cursor.return_value.__enter__.return_value.fetchone.return_value = (40, 40)
            psycopg2 = SimpleNamespace(connect=Mock(return_value=pg))
            remove = Mock(side_effect=[None, 10])
            age_remove = Mock(return_value=7)
            refresh = Mock()
            with (
                patch.dict(sys.modules, {
                    "psycopg2": psycopg2,
                    "sold_cars": SimpleNamespace(remove_confirmed=remove, remove_aged_out=age_remove),
                    "refresh_catalog_queue": SimpleNamespace(main=refresh),
                }),
                patch.object(import_cars, "STATE_PATH", str(state)),
                patch.object(import_cars, "LOCK_PATH", str(lock)),
                patch.object(import_cars, "open_source", return_value=(sq, SimpleNamespace(st_mtime=0), "snapshot")),
                patch.object(import_cars, "load_title_catalog", return_value=({}, {})),
                patch.object(import_cars, "registration_cleanup_plan", return_value=(date(2022, 1, 1), {"old"}, {"old", "site-old"})),
                patch.object(import_cars, "copy_table", side_effect=[10, 40, 10, 40]) as copy,
                redirect_stdout(io.StringIO()),
            ):
                with patch.object(sys, "argv", ["import_cars.py"]):
                    self.assertEqual(import_cars.main(), 3)
                    self.assertEqual(state.read_text(), "snapshot\nsold-delete-blocked\n")
                    pg.__exit__.assert_called_once_with(None, None, None)
                    self.assertEqual(copy.call_count, 2)
                    self.assertEqual(copy.call_args.kwargs["excluded_ids"], {"old", "site-old"})
                    age_remove.assert_called_once_with(pg.cursor.return_value.__enter__.return_value, {"old", "site-old"})
                    self.assertEqual(remove.call_args.kwargs["aged_out_ids"], {"old", "site-old"})
                    refresh.assert_called_once()
                    self.assertEqual(import_cars.main(), 3)
                    self.assertEqual(copy.call_count, 2)
                    self.assertEqual(remove.call_count, 1)
                with patch.object(sys, "argv", ["import_cars.py", "--allow-mass-delete"]):
                    self.assertEqual(import_cars.main(), 0)
                self.assertEqual(state.read_text(), "snapshot\n")
                self.assertTrue(remove.call_args.kwargs["allow_mass_delete"])


if __name__ == "__main__":
    unittest.main()
