import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import sync_seller_translations as sync


class NoTranslationWork(unittest.TestCase):
    def test_empty_export_in_fresh_or_resumed_directory(self):
        for resume in (False, True):
            with self.subTest(resume=resume), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                if resume:
                    (path / "reviewed.jsonl").write_text('{"text": "previous work"}\n')
                argv = ["sync", "--server", "site", "--work-dir", directory]
                with patch.object(sys, "argv", argv), patch.object(
                    sync.subprocess, "check_output", return_value=b'{"terms":[],"descriptions":[]}'
                ), patch.object(sync.subprocess, "run") as workers:
                    sync.main()
                workers.assert_not_called()
                events = [json.loads(s)["event"] for s in (path / "sync-history.jsonl").read_text().splitlines()]
                self.assertEqual(events, ["started", "completed"])
                self.assertEqual((path / "source.jsonl").read_text(), "")
