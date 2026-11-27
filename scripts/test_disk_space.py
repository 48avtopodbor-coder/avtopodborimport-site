import contextlib
import io
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import check_disk_space as disk


def df(kib, *, duplicate=False, code=0):
    row = f"/dev/data 5000000 0 {kib} 10% /data\n"
    return CompletedProcess([], code, "Filesystem 1024-blocks Used Available Capacity Mounted on\n"
                            + row * (2 if duplicate else 1), "")


class SpaceCheckTests(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.state = Path(folder.name) / "attempt"

    def run_check(self, results, now, configured=True):
        output = io.StringIO()
        with patch.object(disk.subprocess, "run", side_effect=results), \
             patch.object(disk.notify, "alert_credentials", return_value=("bot", "chat") if configured else None), \
             patch.object(disk.notify, "deliver_message") as send, \
             patch.object(disk.time, "time", return_value=now), contextlib.redirect_stdout(output):
            status = disk.check(state=self.state)
        return status, send, output.getvalue()

    def test_exact_threshold_is_healthy(self):
        status, send, _ = self.run_check([df(3 * 1024**2), df(4 * 1024**2)], 1)
        self.assertEqual(status, 0)
        send.assert_not_called()
        self.assertFalse(self.state.exists())

    def test_two_low_hosts_one_alert_across_midnight_for_24_hours(self):
        results = [df(3 * 1024**2 - 1, duplicate=True), df(500)]
        _, send, _ = self.run_check(results, 86399)
        message = send.call_args.args[0]
        self.assertEqual(message.count("Сайт,"), 1)
        self.assertEqual(message.count("Сборщик,"), 1)
        _, send, log = self.run_check(results, 86400)
        send.assert_not_called()
        self.assertIn("меньше 3 ГиБ", log)
        self.run_check(results, 86399 + 86400 - 1)[1].assert_not_called()
        self.run_check(results, 86399 + 86400)[1].assert_called_once()

    def test_incomplete_check_keeps_other_readings(self):
        status, send, output = self.run_check([df(10, code=1), TimeoutExpired("ssh", 30)], 100)
        self.assertEqual(status, 1)
        send.assert_called_once()
        self.assertIn("Не удалось проверить место: Сборщик", output)

    def test_without_bot_logs_without_reserving_the_interval(self):
        results = [df(2000), df(4*1024**2)]
        status, send, output = self.run_check(results, 100, configured=False)
        self.assertEqual(status, 0)
        self.assertIn("меньше 3 ГиБ", output)
        self.assertFalse(self.state.exists())
        send.assert_not_called()
        self.run_check(results, 101)[1].assert_called_once()


if __name__ == "__main__":
    unittest.main()
