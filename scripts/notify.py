#!/usr/bin/env python3
"""Report import failures once per published snapshot."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import stat
from urllib.request import Request, urlopen


ALERT_ENV = Path("/etc/avtopodbor-alerts.env")
ALERT_STATE = Path("/srv/che168/import-alerts.state")
IMPORT_COMMAND = "sudo -u postgres python3 /opt/avtopodborimport/import_cars.py"
GUARD_COUNTS = re.compile(r"К удалению (\d+), активных машин на сайте \d+, порог (\d+)")


def alert_credentials(path):
    try:
        info = path.stat()
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600:
            return None
        fields = dict(line.partition("=")[::2] for line in path.read_text().splitlines()
                      if "=" in line and not line.lstrip().startswith("#"))
    except (OSError, UnicodeError):
        return None
    token = fields.get("ALERT_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = fields.get("ALERT_TELEGRAM_CHAT_ID", "").strip()
    if re.fullmatch(r"\d+:[\w-]+", token, re.ASCII) and re.fullmatch(r"-?\d+|@\w+", chat_id, re.ASCII):
        return token, chat_id
    return None


def claim_snapshot(snapshot, state_path):
    info = snapshot.stat()
    identity = f"{info.st_dev}:{info.st_ino}:{info.st_mtime_ns}:{info.st_size}\n"
    fd = os.open(state_path, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a+") as state:
        fcntl.flock(state, fcntl.LOCK_EX)
        state.seek(0)
        if identity in state:
            return False
        state.write(identity)
        state.flush()
        os.fsync(state.fileno())
    return True


def send_alert(snapshot, status, import_log, env_path=ALERT_ENV, state_path=ALERT_STATE):
    if not claim_snapshot(snapshot, state_path):
        return
    counts = GUARD_COUNTS.search(import_log)
    if status == 3:
        detail = f"Кандидатов на удаление {counts[1]}, порог {counts[2]}." if counts else (
            "Число кандидатов и порог смотрите в журнале импорта."
        )
        message = f"AVTOPODBOR IMPORT: предохранитель пропустил удаление снятых машин. {detail}\n"
        message += f"После ручной проверки: {IMPORT_COMMAND} --allow-mass-delete"
    else:
        message = (f"AVTOPODBOR IMPORT: импорт завершился с кодом {status}. "
                   f"Проверка снимка: {IMPORT_COMMAND} --dry-run")

    credentials = alert_credentials(env_path)
    if credentials is None:
        print("Оповещение только в журнале:", message.replace("\n", " "))
        return
    token, chat_id = credentials
    payload = json.dumps({"chat_id": chat_id, "text": message}).encode()
    request = Request(f"https://api.telegram.org/bot{token}/sendMessage", payload,
                      {"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=10) as response:
            sent = json.load(response).get("ok") is True
    except (OSError, ValueError):
        sent = False
    print("Оповещение Telegram отправлено" if sent else "Оповещение Telegram не доставлено")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("status", type=int)
    parser.add_argument("import_log", type=Path)
    args = parser.parse_args()
    send_alert(args.snapshot, args.status, args.import_log.read_text(errors="replace"))


if __name__ == "__main__":
    main()
