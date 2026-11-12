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

SQLITE_PATH = os.environ.get("SQLITE_PATH", "/srv/che168/cars.db")
PG_DSN = os.environ.get(
    "IMPORT_PG_DSN", "postgresql://postgres@/avtopodborimport?host=/var/run/postgresql"
)
LOCK_PATH = "/tmp/import_cars.lock"
# Дата копии, которую уже перенесли (домашняя папка postgres)
STATE_PATH = os.environ.get("IMPORT_STATE", "/var/lib/postgresql/import_cars.last")
BATCH = 1000

# Столбцы машин: одинаковые имена в базе сборщика и в базе сайта.
# local_photo есть только на сайте — импорт его не трогает.
CAR_COLS = [
    "listing_id", "url", "brand_ru", "brand_cn", "model", "year", "mileage_km",
    "price_cny", "price_wan", "gearbox", "fuel", "color", "city", "description", "images",
    "series_name", "spec_id", "province_id", "displacement", "environmental",
    "first_reg_date", "dealer_id", "dealer_name", "publish_date", "is_active",
    "details_json", "drive", "params_text", "power_hp", "engine_ml", "photos", "photo_count",
    "tires", "scraped_at", "updated_at",
]
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
    for c in CAR_COLS:
        if c in CAR_KEEP:
            continue
        if c in CAR_EXACT:
            sets.append(f"{c} = EXCLUDED.{c}")
        else:
            # Не затираем уже собранные данные пустым значением
            sets.append(f"{c} = COALESCE(EXCLUDED.{c}, cars.{c})")
    return (f"INSERT INTO cars ({', '.join(CAR_COLS)}) VALUES %s "
            f"ON CONFLICT (listing_id) DO UPDATE SET {', '.join(sets)}")


def spec_upsert_sql():
    sets = [f"{c} = COALESCE(EXCLUDED.{c}, specs.{c})" for c in SPEC_DST if c != "spec_id"]
    return (f"INSERT INTO specs ({', '.join(SPEC_DST)}) VALUES %s "
            f"ON CONFLICT (spec_id) DO UPDATE SET {', '.join(sets)}")


def open_source():
    if not os.path.exists(SQLITE_PATH):
        sys.exit(f"нет файла {SQLITE_PATH}")
    age = time.time() - os.path.getmtime(SQLITE_PATH)
    if age < 120:
        sys.exit(f"копия обновилась {age:.0f} с назад, возможно, ещё пишется — пропуск")
    # Только чтение и без блокировок: копия не меняется, а у postgres нет прав на запись в папку
    sq = sqlite3.connect(f"file:{SQLITE_PATH}?mode=ro&immutable=1", uri=True)
    for table, cols in (("cars", CAR_COLS), ("specs", SPEC_SRC)):
        have = {row[1] for row in sq.execute(f"PRAGMA table_info({table})")}
        missing = [c for c in cols if c not in have]
        if missing:
            sys.exit(f"в {SQLITE_PATH}, таблица {table}, нет столбцов: {', '.join(missing)}")
    return sq, age


def copy_table(sq, cur, sql, src_cols, table):
    from psycopg2.extras import execute_values
    rows = sq.execute(f"SELECT {', '.join(src_cols)} FROM {table}")
    total = 0
    while True:
        batch = rows.fetchmany(BATCH)
        if not batch:
            break
        execute_values(cur, sql, batch, page_size=BATCH)
        total += len(batch)
    return total


def main():
    dry = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    lock = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit("импорт уже идёт — пропуск")

    t0 = time.time()
    sq, age = open_source()
    n_cars, n_active = sq.execute(
        "SELECT count(*), sum(is_active = 1 AND price_cny > 0) FROM cars").fetchone()
    n_specs = sq.execute("SELECT count(*) FROM specs").fetchone()[0]
    stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(SQLITE_PATH)))
    print(f"{time.strftime('%Y-%m-%d %H:%M')} источник {SQLITE_PATH} от {stamp}: "
          f"машин {n_cars} (в продаже с ценой {n_active}), комплектаций {n_specs}")
    if dry:
        print("проверка источника: ok, в базу сайта ничего не записано")
        return

    mtime = f"{os.path.getmtime(SQLITE_PATH):.0f}"
    try:
        last = open(STATE_PATH).read().strip()
    except OSError:
        last = ""
    if last == mtime and not force:
        print("копия не менялась с прошлого импорта — пропуск")
        return

    import psycopg2
    pg = psycopg2.connect(PG_DSN)
    try:
        with pg, pg.cursor() as cur:  # одна транзакция: сайт видит либо старые данные, либо новые
            s = copy_table(sq, cur, spec_upsert_sql(), SPEC_SRC, "specs")
            c = copy_table(sq, cur, car_upsert_sql(), CAR_COLS, "cars")
            cur.execute("SELECT count(*), count(*) FILTER (WHERE is_active = 1 AND price_cny > 0) FROM cars")
            site_total, site_active = cur.fetchone()
    finally:
        pg.close()
        sq.close()
    with open(STATE_PATH, "w") as f:
        f.write(mtime + "\n")
    print(f"готово за {time.time() - t0:.0f} с: комплектаций {s}, машин {c}; "
          f"на сайте машин {site_total}, в продаже с ценой {site_active}")


if __name__ == "__main__":
    main()
