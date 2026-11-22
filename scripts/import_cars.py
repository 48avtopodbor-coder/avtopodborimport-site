#!/usr/bin/env python3
"""Перенос машин и комплектаций из базы сборщика che168 (SQLite) в базу сайта (PostgreSQL).

Где работает: сервер Timeweb Cloud, файл /opt/avtopodborimport/import_cars.py.
Запуск: crontab root, раз в час в :20, от пользователя postgres:
    sudo -u postgres python3 /opt/avtopodborimport/import_cars.py
Источник: ночная копия базы сборщика, её кладёт pull_db.sh (04:05).

Если копия не менялась с прошлого импорта, запуск пропускается (копия обновляется раз в сутки).

--dry-run  только проверить источник: путь, дата, число строк, нужные столбцы.
--force    импортировать, даже если копия не менялась.
"""
import fcntl
import os
import sqlite3
import sys
import time
from collections import Counter

from car_titles import extract_title, normalize_brand

SQLITE_PATH = os.environ.get("SQLITE_PATH", "/srv/che168/cars.db")
PG_DSN = os.environ.get(
    "IMPORT_PG_DSN", "postgresql://postgres@/avtopodborimport?host=/var/run/postgresql"
)
LOCK_PATH = "/tmp/import_cars.lock"
# Дата копии, которую уже перенесли (домашняя папка postgres)
STATE_PATH = os.environ.get("IMPORT_STATE", "/var/lib/postgresql/import_cars.last")
BATCH = 1000

# Столбцы машин: одинаковые имена в базе сборщика и в базе сайта.
# local_photo, local_photo_2 и local_photo_3 есть только на сайте — импорт их не трогает.
CAR_COLS = [
    "listing_id", "url", "brand_ru", "brand_cn", "model", "year", "mileage_km",
    "price_cny", "price_wan", "gearbox", "fuel", "color", "city", "description", "images",
    "series_name", "spec_id", "province_id", "displacement", "environmental",
    "first_reg_date", "dealer_id", "dealer_name", "publish_date", "is_active",
    "details_json", "drive", "params_text", "power_hp", "engine_ml", "photos", "photo_count",
    "tires", "scraped_at", "updated_at",
]
CAR_DERIVED_COLS = ["brand_id", "model_name", "model_slug", "trim"]
CAR_DST_COLS = CAR_COLS + CAR_DERIVED_COLS
# Эти поля всегда берём из сборщика как есть: продана ли машина и почём.
CAR_EXACT = {"is_active", "price_cny", "price_wan", "updated_at"}
# Эти поля не меняем после первой загрузки: ключ и время появления (от него порядок «сначала свежие»).
CAR_KEEP = {"listing_id", "scraped_at"}

# Комплектации: в сборщике столбец называется full, на сайте is_full.
SPEC_SRC = ["spec_id", "fuel", "drive", "gearbox", "power_hp", "engine_ml",
            "params_text", "params_json", "tires", "full", "fetched_at"]
SPEC_DST = ["spec_id", "fuel", "drive", "gearbox", "power_hp", "engine_ml",
            "params_text", "params_json", "tires", "is_full", "fetched_at"]


def car_upsert_sql():
    sets = []
    for c in CAR_DST_COLS:
        if c in CAR_KEEP:
            continue
        if c in CAR_EXACT or c in CAR_DERIVED_COLS:
            sets.append(f"{c} = EXCLUDED.{c}")
        else:
            # Не затираем уже собранные данные пустым значением
            sets.append(f"{c} = COALESCE(EXCLUDED.{c}, cars.{c})")
    return (f"INSERT INTO cars ({', '.join(CAR_DST_COLS)}) VALUES %s "
            f"ON CONFLICT (listing_id) DO UPDATE SET {', '.join(sets)}")


def spec_upsert_sql():
    sets = [f"{c} = COALESCE(EXCLUDED.{c}, specs.{c})" for c in SPEC_DST if c != "spec_id"]
    return (f"INSERT INTO specs ({', '.join(SPEC_DST)}) VALUES %s "
            f"ON CONFLICT (spec_id) DO UPDATE SET {', '.join(sets)}")


def open_source(published=False):
    if not os.path.exists(SQLITE_PATH):
        sys.exit(f"нет файла {SQLITE_PATH}")
    before = os.stat(SQLITE_PATH)
    age = time.time() - before.st_mtime
    if age < 120 and not published:
        sys.exit(f"копия обновилась {age:.0f} с назад, возможно, ещё пишется — пропуск")
    # Только чтение и без блокировок: копия не меняется, а у postgres нет прав на запись в папку
    sq = sqlite3.connect(f"file:{SQLITE_PATH}?mode=ro&immutable=1", uri=True)
    after = os.stat(SQLITE_PATH)
    if (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size) != (
        after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size
    ):
        sq.close()
        sys.exit("копия базы изменилась во время открытия — повторите импорт")
    for table, cols in (("cars", CAR_COLS), ("specs", SPEC_SRC)):
        have = {row[1] for row in sq.execute(f"PRAGMA table_info({table})")}
        missing = [c for c in cols if c not in have]
        if missing:
            sys.exit(f"в {SQLITE_PATH}, таблица {table}, нет столбцов: {', '.join(missing)}")
    identity = f"{before.st_dev}:{before.st_ino}:{before.st_mtime_ns}:{before.st_size}"
    return sq, before, identity


def load_title_catalog(cur):
    cur.execute("SELECT a.alias_norm, b.id, b.slug FROM brand_aliases a JOIN brands b ON b.id = a.brand_id")
    brands = {alias: (brand_id, slug) for alias, brand_id, slug in cur.fetchall()}
    cur.execute("SELECT b.slug, m.source_series, m.model_name, m.model_slug FROM model_aliases m JOIN brands b ON b.id = m.brand_id")
    models = {}
    for slug, source, name, model_slug in cur.fetchall():
        models.setdefault(slug, {})[source] = (name, model_slug)
    return brands, models


def enrich_car(row, brands, models, unknown):
    data = dict(zip(CAR_COLS, row))
    raw_brand = (data["brand_ru"] or data["brand_cn"] or "").strip()
    found = brands.get(normalize_brand(raw_brand))
    if not found and data["brand_cn"]:
        found = brands.get(normalize_brand(data["brand_cn"]))
    if not found:
        if raw_brand:
            unknown[raw_brand] += 1
        return tuple(row) + (None, None, None, None)
    brand_id, slug = found
    name, model_slug, trim = extract_title(
        data["model"] or "", data["series_name"], data["brand_cn"], models.get(slug, {}), slug
    )
    return tuple(row) + (brand_id, name, model_slug, trim)


def copy_table(sq, cur, sql, src_cols, table, title_catalog=None):
    from psycopg2.extras import execute_values
    rows = sq.execute(f"SELECT {', '.join(src_cols)} FROM {table}")
    total = 0
    unknown = Counter()
    while True:
        batch = rows.fetchmany(BATCH)
        if not batch:
            break
        if title_catalog is not None:
            brands, models = title_catalog
            batch = [enrich_car(row, brands, models, unknown) for row in batch]
        execute_values(cur, sql, batch, page_size=BATCH)
        total += len(batch)
    if unknown:
        execute_values(cur, """INSERT INTO unmapped_brand_names (raw_name, cars_count)
            VALUES %s ON CONFLICT (raw_name) DO UPDATE SET
            cars_count = unmapped_brand_names.cars_count + EXCLUDED.cars_count,
            last_seen = now()""", list(unknown.items()))
    return total


def main():
    dry = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    published = "--published" in sys.argv
    lock = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit("импорт уже идёт — пропуск")

    t0 = time.time()
    sq, source_stat, identity = open_source(published=published)
    n_cars, n_active = sq.execute(
        "SELECT count(*), sum(is_active = 1 AND price_cny > 0) FROM cars").fetchone()
    n_specs = sq.execute("SELECT count(*) FROM specs").fetchone()[0]
    stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(source_stat.st_mtime))
    print(f"{time.strftime('%Y-%m-%d %H:%M')} источник {SQLITE_PATH} от {stamp}: "
          f"машин {n_cars} (в продаже с ценой {n_active}), комплектаций {n_specs}")
    if dry:
        print("проверка источника: ok, в базу сайта ничего не записано")
        return

    try:
        with open(STATE_PATH) as state:
            last = state.read().strip()
    except OSError:
        last = ""
    if last == identity and not force:
        print("копия не менялась с прошлого импорта — пропуск")
        return

    import psycopg2
    pg = psycopg2.connect(PG_DSN)
    try:
        with pg, pg.cursor() as cur:  # одна транзакция: сайт видит либо старые данные, либо новые
            title_catalog = load_title_catalog(cur)
            s = copy_table(sq, cur, spec_upsert_sql(), SPEC_SRC, "specs")
            c = copy_table(sq, cur, car_upsert_sql(), CAR_COLS, "cars", title_catalog)
            cur.execute("SELECT count(*), count(*) FILTER (WHERE is_active = 1 AND price_cny > 0) FROM cars")
            site_total, site_active = cur.fetchone()
    finally:
        pg.close()
        sq.close()
    with open(STATE_PATH, "w") as f:
        f.write(identity + "\n")
    print(f"готово за {time.time() - t0:.0f} с: комплектаций {s}, машин {c}; "
          f"на сайте машин {site_total}, в продаже с ценой {site_active}")


if __name__ == "__main__":
    main()
