import importlib.util
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


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


if __name__ == "__main__":
    unittest.main()
