#!/usr/bin/env python3
"""Delete only queued sold-car files, preserving live references and shared cache."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import pwd
import re
import subprocess
import sys
from sold_cars import ID_RE, cache_keys

PHOTOS = Path("/opt/avtopodborimport/photos")
CACHE = Path("/opt/avtopodborimport/photo-cache")
EXTENSIONS = (".webp", ".jpg", ".jpeg", ".png", ".gif")


def open_lock(name):
    # Linux protected_regular forbids O_CREAT on another user's file in /tmp,
    # even for root. Open an existing lock without O_CREAT or truncation.
    flags = os.O_RDWR | os.O_NOFOLLOW
    try:
        return os.open(name, flags)
    except FileNotFoundError:
        try:
            return os.open(name, flags | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return os.open(name, flags)


def database_plan():
    import psycopg2
    with psycopg2.connect("dbname=avtopodborimport user=postgres") as con:
        with con.cursor() as cur:
            cur.execute("SELECT listing_id,cache_keys FROM sold_car_cleanup WHERE cleaned_at IS NULL")
            jobs = cur.fetchall()
        if not jobs:
            return {"jobs": [], "protected_keys": [], "live_ids": [], "protected_files": []}
        wanted = {key for _, keys in jobs for key in keys}
        protected_keys, live_ids, protected_files = set(), set(), set()
        with con.cursor(name="live_photo_references") as cur:
            cur.itersize = 500
            cur.execute("SELECT listing_id,photos,images,local_photo,local_photo_2,local_photo_3,local_photo_4 FROM cars")
            for lid, photos, images, *paths in cur:
                live_ids.add(str(lid))
                protected_keys.update(cache_keys(photos, images) & wanted)
                for path in paths:
                    if isinstance(path, str) and path.startswith("/photos/"):
                        protected_files.add(path.removeprefix("/photos/"))
    return {"jobs": jobs, "protected_keys": sorted(protected_keys), "live_ids": sorted(live_ids), "protected_files": sorted(protected_files)}


def database_ack(ids):
    import psycopg2
    with psycopg2.connect("dbname=avtopodborimport user=postgres") as con:
        with con.cursor() as cur:
            cur.execute("UPDATE sold_car_cleanup SET cleaned_at=now(),cache_keys='[]'::jsonb WHERE listing_id=ANY(%s)", (ids,))


def clean_files(plan, apply=False):
    protected = set(plan["protected_keys"])
    live = set(plan["live_ids"])
    protected_files = set(plan.get("protected_files", []))
    stats = {"cars": 0, "files": 0, "bytes_released": 0, "shared_references_kept": 0, "errors": 0}
    acknowledged = []
    for lid, keys in plan["jobs"]:
        if not ID_RE.fullmatch(lid):
            raise ValueError("Invalid listing ID")
        if lid in live:
            acknowledged.append(lid)
            continue
        paths = [PHOTOS / (lid + suffix + ext) for suffix in ("", "_2", "_3", "_4") for ext in EXTENSIONS]
        for key in set(keys):
            if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key):
                raise ValueError("Invalid photo cache key")
            if key in protected:
                stats["shared_references_kept"] += 1
            else:
                paths.append(CACHE / key)
        ok = True
        for path in paths:
            if path.parent == PHOTOS and path.name in protected_files:
                continue
            try:
                if not path.is_file() or path.is_symlink():
                    continue
                info = path.stat()
                if apply:
                    path.unlink()
                stats["files"] += 1
                if info.st_nlink == 1:
                    stats["bytes_released"] += info.st_blocks * 512
            except OSError:
                ok = False
                stats["errors"] += 1
        if ok:
            stats["cars"] += 1
            acknowledged.append(lid)
    return stats, acknowledged


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--plan", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--ack", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.plan:
        print(json.dumps(database_plan()))
        return
    if args.ack:
        database_ack(json.load(sys.stdin))
        return
    if os.geteuid() != 0:
        raise SystemExit("Run as root to clean files")
    # Serialize against importer and downloader; preserve postgres ownership after reboot.
    handles = []
    try:
        for name in ("/tmp/import_cars.lock", "/tmp/fetch_photos.lock"):
            fd = open_lock(name)
            handles.append(fd)
            if "import_cars" in name:
                user = pwd.getpwnam("postgres")
                os.fchown(fd, user.pw_uid, user.pw_gid)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print("Cleanup deferred: import/photo batch is running")
                return
        command = ["sudo", "-u", "postgres", sys.executable, str(Path(__file__).resolve())]
        plan = json.loads(subprocess.check_output(command + ["--plan"], text=True, timeout=300))
        stats, ids = clean_files(plan, apply=args.apply)
        if args.apply and ids:
            subprocess.run(command + ["--ack"], input=json.dumps(ids), text=True, check=True, timeout=60)
        print(json.dumps({"applied": args.apply, **stats}))
        if stats["errors"]:
            raise SystemExit(1)
    finally:
        for fd in handles:
            os.close(fd)


if __name__ == "__main__":
    main()
