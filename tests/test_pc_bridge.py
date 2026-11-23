import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pc_bridge_server as bridge
import photo_relay


class BridgeTests(unittest.TestCase):
    def test_direct_mode_ignores_heartbeat_and_does_not_issue_pc_work(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            (state / "alive").touch()
            with patch.object(photo_relay, "BRIDGE_STATE", state):
                self.assertTrue(photo_relay.workstation_alive())
                (state / "disabled").touch()
                self.assertFalse(photo_relay.workstation_alive())
                photo_relay.enqueue_workstation("https://example.autoimg.cn/photo.webp", "a" * 64)
                self.assertFalse((state / "pending").exists())
            with patch.object(bridge, "STATE", state), patch.object(bridge, "database") as query:
                self.assertEqual(bridge.work(12), {"jobs": [], "reason": "direct server mode"})
                query.assert_not_called()

    def test_collector_acknowledgment_preserves_a_newer_request(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            request = state / "collect-request"
            request.write_text("new-request")
            with patch.object(bridge, "STATE", state):
                self.assertFalse(
                    bridge.acknowledge_collector({"request": "old-request"})[
                        "acknowledged"
                    ]
                )
                self.assertTrue(request.exists())
                self.assertTrue(
                    bridge.acknowledge_collector({"request": "new-request"})[
                        "acknowledged"
                    ]
                )
                self.assertFalse(request.exists())

    def test_receiver_preserves_bytes_and_rejects_unrequested_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            cache, photos, pending = [
                base / name for name in ("cache", "photos", "pending")
            ]
            for p in (cache, photos, pending):
                p.mkdir()
            key = "a" * 64
            manifest = base / "work.json"
            manifest.write_text(
                json.dumps({key: {"id": key, "listing_id": "123", "index": 3}})
            )
            data = b"RIFF\x0c\x00\x00\x00WEBPoriginal-bytes"
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode="w") as archive:
                for name, body in (("../../escape", b"bad"), (key + "__p1", data)):
                    member = tarfile.TarInfo(name)
                    member.size = len(body)
                    archive.addfile(member, io.BytesIO(body))
            stream.seek(0)
            with patch.object(bridge, "CACHE", cache), patch.object(
                bridge, "PHOTOS", photos
            ), patch.object(bridge, "PENDING", pending), patch.object(
                bridge, "MANIFEST", manifest
            ), patch.object(
                bridge.sys, "stdin", SimpleNamespace(buffer=stream)
            ), patch.object(
                bridge, "database"
            ) as database, patch.object(
                bridge.shutil,
                "disk_usage",
                return_value=SimpleNamespace(free=10 * 1024**3),
            ):
                result = bridge.receive()
                self.assertEqual(result, {"stored": 1, "catalog_paths": 1})
                self.assertEqual((cache / key).read_bytes(), data)
                self.assertEqual((photos / "123_3.webp").read_bytes(), data)
                self.assertFalse((base / "escape").exists())
                self.assertEqual(
                    database.call_args.args[1], [("123", 3, "/photos/123_3.webp")]
                )

    def test_receiver_does_not_publish_html_as_photo(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            key = "b" * 64
            (base / "pending").mkdir()
            manifest = base / "work.json"
            manifest.write_text(json.dumps({key: {"id": key}}))
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode="w") as archive:
                body = b"<html>blocked</html>"
                member = tarfile.TarInfo(key + "__p1")
                member.size = len(body)
                archive.addfile(member, io.BytesIO(body))
            stream.seek(0)
            with patch.object(bridge, "CACHE", base / "cache"), patch.object(
                bridge, "MANIFEST", manifest
            ), patch.object(bridge.sys, "stdin", SimpleNamespace(buffer=stream)):
                self.assertEqual(bridge.receive()["stored"], 0)
                self.assertFalse((base / "cache" / key).exists())


if __name__ == "__main__":
    unittest.main()
