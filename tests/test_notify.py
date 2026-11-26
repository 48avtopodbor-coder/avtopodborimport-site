from contextlib import redirect_stdout
from io import BytesIO, StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import notify


class NotifyTests(unittest.TestCase):
    def test_guard_alert_includes_counts_and_is_sent_once_for_hard_linked_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot, hardlink = root / "cars.db", root / "copy.db"
            snapshot.touch()
            hardlink.hardlink_to(snapshot)
            env, state = root / "telegram.env", root / "state"
            env.write_text("ALERT_TELEGRAM_BOT_TOKEN=123:mock-secret\nALERT_TELEGRAM_CHAT_ID=-456\n")
            env.chmod(0o600)
            log = "ПРЕДОХРАНИТЕЛЬ: удаление пропущено. К удалению 301, активных машин на сайте 1000, порог 300"
            output = StringIO()
            with patch.object(notify, "urlopen", return_value=BytesIO(b'{"ok": true}')) as post, redirect_stdout(output):
                notify.send_alert(snapshot, 3, log, env, state)
                notify.send_alert(hardlink, 3, log, env, state)
            post.assert_called_once()
            payload = json.loads(post.call_args.args[0].data)
            self.assertEqual(payload["chat_id"], "-456")
            self.assertIn("Кандидатов на удаление 301, порог 300", payload["text"])
            self.assertIn("--allow-mass-delete", payload["text"])
            self.assertNotIn("mock-secret", output.getvalue())

    def test_missing_config_logs_error_without_sending(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "cars.db"
            snapshot.touch()
            output = StringIO()
            with patch.object(notify, "urlopen") as post, redirect_stdout(output):
                notify.send_alert(snapshot, 1, "", root / "missing", root / "state")
            post.assert_not_called()
            self.assertIn("импорт завершился с кодом 1", output.getvalue())
