#!/usr/bin/env python3
"""Check the photo and backup filesystems on both catalog hosts."""
import fcntl
import os
from pathlib import Path
import subprocess
import time

import notify


GIB = 1024 ** 3
LOW_BYTES = 3 * GIB
ALERT_INTERVAL = 24 * 3600
STATE = Path("/var/lib/avtopodbor-disk-space/last-attempt")
PROBES = {
    "Сайт": ["df", "-Pk", "/opt/avtopodborimport/photos", "/var/backups/avtopodbor-catalog"],
    "Сборщик": [
        "ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", "hosting",
        'LC_ALL=C df -Pk "$HOME/che168/data" "$HOME/avto-private-backups/postgres"',
    ],
}


def available_filesystems(output):
    """POSIX df -Pk emits one row per path, including paths on the same mount."""
    mounts = {}
    for line in output.splitlines()[1:]:
        device, _, _, available, _, mount = line.split(maxsplit=5)
        key = (device, mount)
        free = int(available) * 1024
        mounts[key] = min(free, mounts.get(key, free))
    return mounts


def reserve_attempt(state, now):
    fd = os.open(state, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, "r+") as out:
        fcntl.flock(out, fcntl.LOCK_EX)
        previous = out.read().strip()
        if previous and now - int(previous) < ALERT_INTERVAL:
            return False
        out.seek(0)
        out.write(f"{now}\n")
        out.truncate()
        out.flush()
        os.fsync(out.fileno())
        return True


def check(*, state=STATE):
    low = []
    complete = True
    for host, command in PROBES.items():
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30,
                                    env={**os.environ, "LC_ALL": "C"})
            mounts = available_filesystems(result.stdout)
            for (device, mount), free in mounts.items():
                detail = f"{host}, раздел {mount} ({device}), свободно {free / GIB:.3f} ГиБ ({free // 1024} КиБ)"
                print(detail, flush=True)
                if free < LOW_BYTES:
                    low.append(detail)
            if result.returncode or not mounts:
                print(f"Не все разделы проверены: {host}, код df/SSH {result.returncode}", flush=True)
                complete = False
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            print(f"Не удалось проверить место: {host} ({type(error).__name__})", flush=True)
            complete = False

    if low:
        message = "AVTOPODBOR IMPORT: свободно меньше 3 ГиБ.\n" + "\n".join(low)
        print(message, flush=True)
        credentials = notify.alert_credentials(notify.ALERT_ENV)
        if credentials and reserve_attempt(state, int(time.time())):
            notify.deliver_message(message, credentials)
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(check())
