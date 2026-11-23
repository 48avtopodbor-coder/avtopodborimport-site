"""Queue file cleanup in the same transaction that removes confirmed inactive cars."""
import hashlib
import json
import re

ID_RE = re.compile(r"[0-9A-Za-z_-]{1,40}\Z")


def cache_keys(*values):
    keys = set()
    for value in values:
        try:
            urls = json.loads(value) if isinstance(value, str) else value
        except (ValueError, TypeError):
            continue
        if not isinstance(urls, list):
            continue
        for url in urls:
            if isinstance(url, str) and url:
                keys.add(hashlib.sha256(url.encode()).hexdigest())
    return keys


def remove_confirmed(sq, cur):
    from psycopg2.extras import execute_values, Json
    ids = [str(row[0]) for row in sq.execute("SELECT listing_id FROM cars WHERE is_active=0")]
    if not ids:
        return 0
    if not all(ID_RE.fullmatch(value) for value in ids):
        raise ValueError("Invalid inactive listing ID; deletion cancelled")
    cur.execute("CREATE TEMP TABLE confirmed_sold_ids(listing_id text PRIMARY KEY) ON COMMIT DROP")
    execute_values(cur, "INSERT INTO confirmed_sold_ids VALUES %s", [(value,) for value in ids])
    cur.execute("""SELECT c.listing_id,c.photos,c.images FROM cars c
        JOIN confirmed_sold_ids s ON s.listing_id=c.listing_id::text FOR UPDATE OF c""")
    jobs = [(str(lid), Json(sorted(cache_keys(photos, images)))) for lid, photos, images in cur.fetchall()]
    if jobs:
        execute_values(cur, """INSERT INTO sold_car_cleanup(listing_id,cache_keys) VALUES %s
            ON CONFLICT(listing_id) DO UPDATE SET
            cache_keys=sold_car_cleanup.cache_keys || EXCLUDED.cache_keys,
            queued_at=now(),cleaned_at=NULL""", jobs)
    cur.execute("DELETE FROM cars c USING confirmed_sold_ids s WHERE c.listing_id::text=s.listing_id")
    return cur.rowcount
