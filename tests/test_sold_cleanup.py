import hashlib
from contextlib import closing, redirect_stdout
import io
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cleanup_sold_photos as local
from cleanup_collector_photos import cleanup
from sold_cars import remove_confirmed


class SoldCleanupTests(unittest.TestCase):
    def test_lock_open_preserves_existing_contents_and_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lock"
            path.write_text("existing lock")
            fd = local.open_lock(str(path))
            os.close(fd)
            self.assertEqual(path.read_text(), "existing lock")
            link = Path(directory) / "link"
            link.symlink_to(path)
            with self.assertRaises(OSError):
                local.open_lock(str(link))

    def test_inactive_files_deleted_but_live_shared_cache_and_outside_paths_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            photos, cache = base / "photos", base / "cache"
            photos.mkdir(); cache.mkdir()
            shared, sold = hashlib.sha256(b"shared").hexdigest(), hashlib.sha256(b"sold").hexdigest()
            (cache / shared).write_bytes(b"shared-image")
            (cache / sold).write_bytes(b"sold-image")
            os.link(cache / sold, photos / "123_4.webp")
            (photos / "123.jpg").write_bytes(b"sold-main")
            (photos / "456.webp").write_bytes(b"live")
            (photos / "123_3.webp").write_bytes(b"shared-local-file")
            outside = base / "outside"; outside.write_bytes(b"keep")
            (photos / "123_2.jpg").symlink_to(outside)
            plan = {"jobs": [["123", [sold, shared]], ["456", []]], "live_ids": ["456"], "protected_keys": [shared], "protected_files": ["123_3.webp"]}
            with patch.object(local, "PHOTOS", photos), patch.object(local, "CACHE", cache):
                dry, _ = local.clean_files(plan)
                self.assertTrue((photos / "123_4.webp").exists())
                actual, ack = local.clean_files(plan, apply=True)
                self.assertFalse((cache / sold).exists())
                self.assertFalse((photos / "123_4.webp").exists())
                self.assertTrue((cache / shared).exists())
                self.assertEqual((photos / "456.webp").read_bytes(), b"live")
                self.assertEqual((photos / "123_3.webp").read_bytes(), b"shared-local-file")
                self.assertEqual(outside.read_bytes(), b"keep")
                self.assertEqual(actual["errors"], 0)
                self.assertEqual(actual["files"], 3)
                self.assertIn("123", ack)
                local.clean_files(plan, apply=True)  # retry after interruption is harmless
                with self.assertRaises(ValueError):
                    local.clean_files({"jobs": [["../../outside", []]], "live_ids": [], "protected_keys": []}, True)

    def test_collector_keeps_active_unknown_and_null_status_records(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); database = base / "cars.db"
            with closing(sqlite3.connect(database)) as con, con:
                con.execute("CREATE TABLE cars(listing_id text, is_active integer)")
                con.executemany("INSERT INTO cars VALUES (?,?)", [("123", 0), ("456", 1), ("789", None)])
            for name in ("123.webp", "123_4.webp", "456.webp", "789.webp", "999.webp"):
                (base / name).write_bytes(b"image")
            self.assertEqual(cleanup(database, base)["files"], 2)
            self.assertTrue((base / "123.webp").exists())
            self.assertEqual(cleanup(database, base, True)["files"], 2)
            for name in ("456.webp", "789.webp", "999.webp"):
                self.assertTrue((base / name).exists())
            with closing(sqlite3.connect(database)) as con:
                self.assertEqual(con.execute("SELECT count(*) FROM cars").fetchone()[0], 3)


class SoldDeletionTests(unittest.TestCase):
    def setUp(self):
        self.source = sqlite3.connect(":memory:")
        self.addCleanup(self.source.close)
        self.source.execute("CREATE TABLE cars(listing_id text, is_active integer)")
        self.source.executemany("INSERT INTO cars VALUES (?, 0)", [(str(n),) for n in range(800)])
        self.cursor = Mock()
        self.execute_values = Mock()
        extras = SimpleNamespace(execute_values=self.execute_values, Json=lambda value: value)
        modules = patch.dict(sys.modules, {"psycopg2.extras": extras})
        modules.start()
        self.addCleanup(modules.stop)

    def remove(self, matches, active, **kwargs):
        self.cursor.fetchall.return_value = [(str(n), None, None) for n in range(matches)]
        self.cursor.fetchone.return_value = (active,)
        self.cursor.rowcount = matches
        return remove_confirmed(self.source, self.cursor, **kwargs)

    def assert_no_cleanup_or_delete(self):
        self.assertEqual(self.execute_values.call_count, 1)  # candidate IDs only
        self.assertFalse(any("DELETE FROM cars" in call.args[0] for call in self.cursor.execute.call_args_list))

    def test_removes_matching_rows_at_limit_and_ignores_absent_ids(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.remove(matches=400, active=8019), 400)
        self.assertEqual(len(self.execute_values.call_args.args[2]), 400)
        self.assertIn("sold_car_cleanup", self.execute_values.call_args.args[1])
        self.assertEqual(self.cursor.execute.call_args.args[1], ([str(n) for n in range(400)],))

    def test_blocks_above_floor_without_enqueuing_cleanup(self):
        log = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(log):
            self.assertIsNone(self.remove(matches=301, active=1000))
        self.assert_no_cleanup_or_delete()
        self.assertIn("ПРЕДОХРАНИТЕЛЬ", log.getvalue())
        self.assertIn("К удалению 301, активных машин на сайте 1000, порог 300", log.getvalue())

    def test_fractional_percent_is_configurable(self):
        with patch.dict(os.environ, {"SOLD_DELETE_MAX_PERCENT": "3.5"}), redirect_stdout(io.StringIO()):
            self.assertIsNone(self.remove(matches=351, active=10010))
        self.assert_no_cleanup_or_delete()

    def test_manual_override_allows_mass_deletion(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.remove(matches=500, active=1000, allow_mass_delete=True), 500)
        self.assertEqual(len(self.execute_values.call_args.args[2]), 500)
        self.assertIn("DELETE FROM cars", self.cursor.execute.call_args.args[0])
