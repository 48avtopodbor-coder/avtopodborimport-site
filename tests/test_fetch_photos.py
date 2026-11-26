import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_photos as photos


class FetchPhotosTests(unittest.TestCase):
    def test_default_selects_only_first_and_second_photos(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(photos, "LOCK_PATH", str(Path(directory) / "lock")),
                patch.object(photos, "psql", side_effect=["0", ""]) as query,
                patch.dict(photos.os.environ, {"PHOTOS_FETCH_CMD": "test-transport"}),
                patch.object(sys, "argv", ["fetch_photos", "--dry-run"]),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                photos.main()
        self.assertEqual(query.call_count, 2)
        for call in query.call_args_list:
            self.assertIn("AND photo_index <= 2", call.args[0])

    def test_fourth_photo_stream_preserves_large_original_and_earlier_files(self):
        # Exercise the real SSH/tar program locally with a deterministic HTTP source.
        transport = '''import http.client,sys
class Response:
 status=200
 will_close=False
 def read(self): return b"RIFF"+b"0000WEBP"+b"x"*(4*1024*1024+100)
 def getheader(self,key): return "image/webp"
class Connection:
 def __init__(self,*args,**kwargs): pass
 def request(self,*args,**kwargs): pass
 def getresponse(self): return Response()
 def close(self): pass
http.client.HTTPSConnection=Connection
exec(sys.stdin.read())
'''
        expected = b"RIFF0000WEBP" + b"x" * (4 * 1024 * 1024 + 100)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for suffix in ("", "_2", "_3"):
                (base / ("123" + suffix + ".webp")).write_bytes(b"earlier-photo")
            writes = []

            def query(sql):
                if sql.startswith("WITH v("):
                    writes.append(sql)
                    return ""
                if "AS photo(photo_index, url, local_path)" in sql:
                    return "123|4|https://example.autoimg.cn/original.webp\n" if "SELECT listing_id, photo_index, url" in sql else "1"
                return "1|1|1|1|1"

            with (
                patch.object(photos, "PHOTOS_DIR", directory),
                patch.object(photos, "LOCK_PATH", str(base / "lock")),
                patch.object(photos, "COOLDOWN_PATH", str(base / "cooldown")),
                patch.object(photos, "FAILED_PATH", str(base / "failed.json")),
                patch.object(photos, "FETCH_CMD", [sys.executable, "-u", "-c", transport]),
                patch.dict(photos.os.environ, {"PHOTOS_FETCH_CMD": "test-transport"}),
                patch.object(photos, "psql", side_effect=query),
                patch.object(sys, "argv", ["fetch_photos", "--limit", "1", "--photo-index", "4"]),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                photos.main()
            self.assertEqual((base / "123_4.webp").read_bytes(), expected)
            for suffix in ("", "_2", "_3"):
                self.assertEqual((base / ("123" + suffix + ".webp")).read_bytes(), b"earlier-photo")
            self.assertTrue(any("local_photo_4 = COALESCE" in sql and "123_4.webp" in sql for sql in writes))
