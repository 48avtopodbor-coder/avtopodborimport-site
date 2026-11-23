import hashlib
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cleanup_sold_photos as local
from cleanup_collector_photos import cleanup


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
