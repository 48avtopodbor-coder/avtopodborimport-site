"""Queue file cleanup in the same transaction that removes listings."""
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
import re

ID_RE = re.compile(r"[0-9A-Za-z_-]{1,40}\Z")
SOLD_DELETE_MIN_LIMIT = 300


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


def remove_confirmed(sq, cur, *, allow_mass_delete=False, aged_out_ids=()):
    """Return the number deleted, or None if the safeguard blocked deletion."""
    from psycopg2.extras import execute_values
    ids = [str(row[0]) for row in sq.execute("SELECT listing_id FROM cars WHERE is_active=0")]
    if not ids:
        return 0
    if not all(ID_RE.fullmatch(value) for value in ids):
        raise ValueError("Invalid inactive listing ID; deletion cancelled")
    cur.execute("CREATE TEMP TABLE confirmed_sold_ids(listing_id text PRIMARY KEY) ON COMMIT DROP")
    execute_values(cur, "INSERT INTO confirmed_sold_ids VALUES %s", [(value,) for value in ids])
    cur.execute("""SELECT c.listing_id,c.photos,c.images FROM cars c
        JOIN confirmed_sold_ids s ON s.listing_id=c.listing_id::text
        WHERE NOT (s.listing_id = ANY(%s::text[])) FOR UPDATE OF c""", (list(aged_out_ids),))
    matching = cur.fetchall()
    if not matching:
        return 0
    if not allow_mass_delete:
        try:
            percent = Decimal(os.environ.get("SOLD_DELETE_MAX_PERCENT", "5"))
        except InvalidOperation as error:
            raise ValueError("SOLD_DELETE_MAX_PERCENT должен быть числом от 0 до 100") from error
        if not percent.is_finite() or not 0 <= percent <= 100:
            raise ValueError("SOLD_DELETE_MAX_PERCENT должен быть числом от 0 до 100")
        cur.execute("SELECT count(*) FROM cars WHERE is_active = 1")
        active = cur.fetchone()[0]
        limit = max(SOLD_DELETE_MIN_LIMIT, int(active * percent / 100))
        if len(matching) > limit:
            print(f"ПРЕДОХРАНИТЕЛЬ: удаление пропущено. К удалению {len(matching)}, активных машин "
                  f"на сайте {active}, порог {limit} (минимум {SOLD_DELETE_MIN_LIMIT}, "
                  f"настройка {percent}%).", flush=True)
            return None
    return queue_and_delete(cur, matching)


def remove_aged_out(cur, ids):
    if not ids:
        return 0
    cur.execute("""SELECT listing_id,photos,images FROM cars
        WHERE listing_id::text = ANY(%s::text[]) FOR UPDATE""", (list(ids),))
    return queue_and_delete(cur, cur.fetchall())


def queue_and_delete(cur, matching):
    from psycopg2.extras import execute_values, Json
    if not matching:
        return 0
    if not all(ID_RE.fullmatch(str(lid)) for lid, _, _ in matching):
        raise ValueError("Invalid listing ID; deletion cancelled")
    jobs = [(str(lid), Json(sorted(cache_keys(photos, images)))) for lid, photos, images in matching]
    execute_values(cur, """INSERT INTO sold_car_cleanup(listing_id,cache_keys) VALUES %s
        ON CONFLICT(listing_id) DO UPDATE SET
        cache_keys=sold_car_cleanup.cache_keys || EXCLUDED.cache_keys,
        queued_at=now(),cleaned_at=NULL""", jobs)
    cur.execute("DELETE FROM cars WHERE listing_id::text = ANY(%s)", ([lid for lid, _ in jobs],))
    return cur.rowcount
