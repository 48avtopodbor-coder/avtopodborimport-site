#!/usr/bin/env python3
"""Server side of the temporary workstation bridge. Invoked only over existing SSH."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time

from photo_relay import CACHE, allowed, image_type

STATE = Path("/srv/che168/pc-bridge")
PENDING = STATE / "pending"
MANIFEST = STATE / "work.json"
FAILED = STATE / "failed.json"
PHOTOS = Path("/opt/avtopodborimport/photos")


def database(code, data=None):
    result = subprocess.run(
        ["sudo", "-u", "postgres", "python3", "-c", code],
        input=json.dumps(data).encode() if data is not None else None,
        capture_output=True,
        check=True,
        timeout=120,
    )
    return json.loads(result.stdout) if result.stdout else None


def atomic_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False))
    temporary.replace(path)


def work(limit):
    if (STATE / "disabled").exists():
        return {"jobs": [], "reason": "direct server mode"}
    STATE.mkdir(parents=True, exist_ok=True)
    PENDING.mkdir(exist_ok=True)
    (STATE / "alive").touch()
    request = STATE / "collect-request"
    control = (
        {"collect_request": request.read_text().strip()} if request.exists() else {}
    )
    if shutil.disk_usage(CACHE).free < 4 * 1024**3:
        return {"jobs": [], "reason": "disk reserve", **control}
    failed = json.loads(FAILED.read_text()) if FAILED.exists() else {}
    jobs = {}
    for p in sorted(
        PENDING.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        try:
            job = json.loads(p.read_text())
            key = hashlib.sha256(job["url"].encode()).hexdigest()
            if not allowed(job["url"]):
                p.unlink()
                continue
            if (CACHE / key).exists():
                p.unlink()
                continue
            if failed.get(key, 0) > time.time():
                continue
            jobs[key] = {"id": key, "url": job["url"]}
            if len(jobs) >= limit:
                break
        except (ValueError, KeyError, OSError):
            continue
    if len(jobs) < limit:
        rows = database("""import psycopg2,json
from psycopg2.extras import RealDictCursor
from pathlib import Path
import sys
sys.path.insert(0,"/opt/avtopodborimport")
from fetch_photos import CANDIDATES_SQL
with psycopg2.connect("dbname=avtopodborimport user=postgres") as c:
 with c.cursor() as cur:
  cur.execute(CANDIDATES_SQL % 2000)
  print(json.dumps(cur.fetchall()))
""")
        for listing_id, index, url in rows:
            key = hashlib.sha256(url.encode()).hexdigest()
            if not allowed(url) or failed.get(key, 0) > time.time():
                continue
            # A request from the gallery may be the same photo as a background job.
            jobs.setdefault(key, {"id": key, "url": url})
            jobs[key].update(listing_id=listing_id, index=index)
            if len(jobs) >= limit:
                break
    atomic_json(MANIFEST, jobs)
    return {"jobs": list(jobs.values()), **control}


def receive():
    jobs = json.loads(MANIFEST.read_text())
    updates = []
    count = 0
    CACHE.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=sys.stdin.buffer, mode="r|") as archive:
        for member in archive:
            key = member.name.removesuffix("__p1")
            if key not in jobs or member.name != key + "__p1" or not member.isfile():
                continue
            data = archive.extractfile(member).read()
            content_type = image_type(data)
            if not content_type or shutil.disk_usage(CACHE).free < 4 * 1024**3:
                continue
            target = CACHE / key
            with tempfile.NamedTemporaryFile(dir=CACHE, delete=False) as f:
                temporary = Path(f.name)
                f.write(data)
            try:
                temporary.chmod(0o644)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
            job = jobs[key]
            lid, index = job.get("listing_id"), job.get("index")
            if (
                lid
                and re.fullmatch(r"[0-9A-Za-z_-]{1,40}", str(lid))
                and index in (1, 2, 3, 4)
            ):
                extension = {
                    "image/webp": ".webp",
                    "image/jpeg": ".jpg",
                    "image/png": ".png",
                    "image/gif": ".gif",
                }[content_type]
                name = str(lid) + ("" if index == 1 else "_" + str(index)) + extension
                final = PHOTOS / name
                link = PHOTOS / (name + ".pc-part")
                link.unlink(missing_ok=True)
                os.link(target, link)
                link.replace(final)
                updates.append((str(lid), index, "/photos/" + name))
            (PENDING / (key + ".json")).unlink(missing_ok=True)
            count += 1
    if updates:
        database(
            """import psycopg2,json,sys
rows=json.load(sys.stdin)
with psycopg2.connect("dbname=avtopodborimport user=postgres") as c:
 with c.cursor() as cur:
  for lid,index,path in rows:
   column=("local_photo","local_photo_2","local_photo_3","local_photo_4")[index-1]
   cur.execute("UPDATE cars SET "+column+"=COALESCE("+column+",%s) WHERE listing_id=%s",(path,lid))
""",
            updates,
        )
    return {"stored": count, "catalog_paths": len(updates)}


def failed(keys):
    values = json.loads(FAILED.read_text()) if FAILED.exists() else {}
    for key in keys:
        if re.fullmatch("[0-9a-f]{64}", key):
            values[key] = time.time() + 24 * 3600
    atomic_json(FAILED, {k: v for k, v in values.items() if v > time.time()})


def acknowledge_collector(data):
    request = STATE / "collect-request"
    with (STATE / "collect.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if request.exists() and request.read_text().strip() == data.get("request"):
            request.unlink()
            return {"acknowledged": True}
    return {"acknowledged": False}


def snapshot():
    folder = Path("/srv/che168")
    with tempfile.NamedTemporaryFile(
        dir=folder, prefix="cars.db.pc-", delete=False
    ) as f:
        temp = Path(f.name)
        shutil.copyfileobj(sys.stdin.buffer, f, 1024 * 1024)
    try:
        with sqlite3.connect("file:" + str(temp) + "?mode=ro", uri=True) as con:
            if con.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Invalid snapshot")
            count = con.execute("SELECT count(*) FROM cars").fetchone()[0]
            con.execute("SELECT count(*) FROM specs").fetchone()
        if count == 0:
            raise ValueError("Empty snapshot")
        temp.chmod(0o644)
        subprocess.run(
            [
                "sudo",
                "-u",
                "postgres",
                "env",
                "SQLITE_PATH=" + str(temp),
                "python3",
                "/opt/avtopodborimport/import_cars.py",
                "--published",
                "--dry-run",
            ],
            check=True,
            stdout=sys.stderr,
            timeout=120,
        )
        previous = folder / "cars.db.pc-previous"
        previous.unlink(missing_ok=True)
        os.link(folder / "cars.db", previous)
        previous.replace(folder / "cars.db.prev")
        temp.replace(folder / "cars.db")
        subprocess.run(
            [
                "sudo",
                "-u",
                "postgres",
                "python3",
                "/opt/avtopodborimport/import_cars.py",
                "--published",
            ],
            check=True,
            stdout=sys.stderr,
            timeout=600,
        )
        subprocess.run(
            [
                "sudo",
                "-u",
                "postgres",
                "python3",
                "/opt/avtopodborimport/translate_seller_descriptions.py",
                "--limit",
                "2000",
            ],
            check=True,
            stdout=sys.stderr,
            timeout=300,
        )
        return {"snapshot_cars": count}
    finally:
        temp.unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "command", choices=("work", "receive", "failed", "snapshot", "ack-collect")
    )
    p.add_argument("--limit", type=int, default=24)
    a = p.parse_args()
    if not 1 <= a.limit <= 100:
        p.error("limit must be 1..100")
    if a.command == "work":
        result = work(a.limit)
    elif a.command == "receive":
        result = receive()
    elif a.command == "snapshot":
        result = snapshot()
    elif a.command == "ack-collect":
        result = acknowledge_collector(json.load(sys.stdin))
    else:
        result = failed(json.load(sys.stdin))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
