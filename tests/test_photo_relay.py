import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from photo_relay import PhotoCache


class PhotoCacheTests(unittest.TestCase):
    def test_startup_and_writes_trim_least_recently_used_files(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            block = os.statvfs(base).f_frsize
            keys = [digit * 64 for digit in "1234"]
            for index, key in enumerate(keys[:3], start=1):
                path = base / key
                path.write_bytes(b"photo")
                os.utime(path, (index, index))
            unrelated = base / "unrelated"
            unrelated.write_bytes(b"outside the cache")

            cache = PhotoCache(base, 2 * block)
            self.assertIsNone(cache.read(keys[0]))
            self.assertEqual(cache.read(keys[1]), b"photo")

            cache.store(keys[3], b"original photo bytes")
            self.assertIsNone(cache.read(keys[2]))
            self.assertEqual(cache.read(keys[1]), b"photo")
            self.assertEqual(cache.read(keys[3]), b"original photo bytes")
            self.assertLessEqual(cache.used, cache.limit)
            self.assertTrue(unrelated.exists())

    def test_large_images_and_low_disk_space_skip_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            cache = PhotoCache(base, os.statvfs(base).f_frsize)
            cache.store("a" * 64, b"x" * (cache.limit + 1))
            with patch("photo_relay.shutil.disk_usage") as usage:
                usage.return_value.free = 0
                cache.store("b" * 64, b"photo")
            self.assertEqual(list(base.iterdir()), [])
