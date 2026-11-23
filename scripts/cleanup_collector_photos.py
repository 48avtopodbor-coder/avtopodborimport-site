#!/usr/bin/env python3
"""Remove legacy collector photo files for explicit SQLite is_active=0 records."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3


def cleanup(database, folder, apply=False):
    files = size = 0
    with closing(sqlite3.connect(f"file:{database}?mode=ro", uri=True)) as con:
        con.execute("BEGIN")
        inactive = {str(row[0]) for row in con.execute("SELECT listing_id FROM cars WHERE is_active=0")}
        for path in Path(folder).iterdir():
            match = re.fullmatch(r"([0-9A-Za-z-]{1,40})(?:_[234])?\.(webp|jpg|jpeg|png|gif)", path.name)
            if not match or match[1] not in inactive or not path.is_file() or path.is_symlink():
                continue
            size += path.stat().st_size
            files += 1
            if apply:
                path.unlink()
    return {"applied": apply, "files": files, "bytes": size}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    from config import DB_PATH
    print(json.dumps(cleanup(Path(DB_PATH).resolve(), Path(__file__).resolve().parent / "photos", args.apply)))
