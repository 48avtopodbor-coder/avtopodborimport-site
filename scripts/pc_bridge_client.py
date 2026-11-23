#!/usr/bin/env python3
"""Temporary encrypted collector → workstation → website transfer, without re-encoding."""

import argparse
import fcntl
import json
from pathlib import Path
import subprocess
import tempfile
import time

from fetch_photos import REMOTE_CODE

SERVER = "/opt/avtopodborimport/pc_bridge_server.py"


def ssh(config, host, command):
    return ["ssh", "-F", str(config), host, command]


def call(config, command, data=None, timeout=180):
    result = subprocess.run(
        ssh(config, "avto-site", "python3 " + SERVER + " " + command),
        input=data,
        capture_output=True,
        timeout=timeout,
        check=True,
    )
    return json.loads(result.stdout)


def transfer_snapshot(config, refresh):
    if refresh:
        subprocess.run(
            ssh(config, "avto-collector", "sh /home/c/cc14862/che168/backup.sh"),
            check=True,
            timeout=600,
        )
    source = subprocess.Popen(
        ssh(config, "avto-collector", "cat /home/c/cc14862/che168/data/cars_backup.db"),
        stdout=subprocess.PIPE,
    )
    target = subprocess.Popen(
        ssh(config, "avto-site", "python3 " + SERVER + " snapshot"), stdin=source.stdout
    )
    source.stdout.close()
    try:
        target_code = target.wait(timeout=900)
        source_code = source.wait(timeout=30)
        if target_code or source_code:
            raise RuntimeError(
                "Snapshot transfer failed; previous website database remains usable"
            )
    finally:
        for process in (source, target):
            if process.poll() is None:
                process.kill()
                process.wait()


def batch(config, limit):
    work = call(config, "work --limit " + str(limit))
    if work.get("collect_request"):
        subprocess.run(
            ssh(
                config,
                "avto-collector",
                "cd /home/c/cc14862/che168 || exit 1; : > data/empty; setsid nohup sh run_hourly.sh > data/start.log 2>&1 < data/empty &",
            ),
            capture_output=True,
            timeout=30,
            check=True,
        )
        call(
            config,
            "ack-collect",
            json.dumps({"request": work["collect_request"]}).encode(),
        )
        print(
            time.strftime("%Y-%m-%d %H:%M:%S"),
            "Collector start request delivered",
            flush=True,
        )
    jobs = work["jobs"]
    if not jobs:
        return 0
    params = {
        "items": [(j["id"], 1, j["url"]) for j in jobs],
        "minutes": 2,
        "pause": 0.3,
        "max_refused": 3,
    }
    program = (REMOTE_CODE + "\nmain(%r)\n" % json.dumps(params)).encode()
    with tempfile.TemporaryFile() as archive:
        result = subprocess.run(
            ssh(config, "avto-collector", "python3 -u -"),
            input=program,
            stdout=archive,
            stderr=subprocess.PIPE,
            timeout=180,
        )
        stats = None
        for line in result.stderr.decode("utf-8", "replace").splitlines():
            if line.startswith("RESULT "):
                stats = json.loads(line[7:])
        if result.returncode or stats is None:
            raise RuntimeError(
                "Collector transfer failed: "
                + result.stderr.decode("utf-8", "replace")[-300:]
            )
        archive.seek(0)
        delivered = subprocess.run(
            ssh(config, "avto-site", "python3 " + SERVER + " receive"),
            stdin=archive,
            capture_output=True,
            timeout=180,
            check=True,
        )
        receipt = json.loads(delivered.stdout)
        failed = [key.rsplit(":", 1)[0] for key in stats.get("failed", [])]
        if failed:
            call(config, "failed", json.dumps(failed).encode())
        print(time.strftime("%Y-%m-%d %H:%M:%S"), json.dumps(receipt), flush=True)
        if stats["stop"] == "refused":
            # Respect the same two-hour cooling-off period as the server downloader.
            time.sleep(2 * 3600)
        elif stats["stop"] == "no-connection":
            time.sleep(120)
        return receipt["stored"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--state-dir", type=Path, required=True)
    p.add_argument("--limit", type=int, default=24)
    p.add_argument("--once", action="store_true")
    p.add_argument("--snapshot", action="store_true")
    p.add_argument("--refresh-snapshot", action="store_true")
    a = p.parse_args()
    if not 1 <= a.limit <= 100:
        p.error("limit must be 1..100")
    a.state_dir.mkdir(parents=True, exist_ok=True)
    if a.snapshot:
        with (a.state_dir / "snapshot.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            transfer_snapshot(a.config, a.refresh_snapshot)
        return
    with (a.state_dir / "photos.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            try:
                count = batch(a.config, a.limit)
                if a.once:
                    return
                time.sleep(1 if count else 5)
            except (subprocess.SubprocessError, OSError, ValueError, RuntimeError) as e:
                print(
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    type(e).__name__,
                    str(e),
                    flush=True,
                )
                if a.once:
                    raise
                time.sleep(30)


if __name__ == "__main__":
    main()
