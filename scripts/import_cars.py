#!/usr/bin/env python3
"""Перенос машин и комплектаций из базы сборщика che168 (SQLite) в базу сайта (PostgreSQL).

Где работает: сервер Timeweb Cloud, файл /opt/avtopodborimport/import_cars.py.
Запуск: crontab root, раз в час в :20, от пользователя postgres:
    sudo -u postgres python3 /opt/avtopodborimport/import_cars.py
Источник: проверенная копия базы сборщика, её кладёт pull_db.sh (04:05 и 16:05 МСК).

Если копия не менялась с прошлого импорта, запуск пропускается (копия обновляется дважды в сутки).

--dry-run  проверить источник и посчитать удаление по возрасту без записи.
--force    импортировать, даже если копия не менялась.
--allow-mass-delete  разрешить удаление выше порога и повторную обработку той же копии.
--normalize-photo-links  исправить ссылки у активных машин без локального главного фото.
                        С --dry-run только посчитать объявления для исправления.

Код 3 означает, что импорт выполнен, но предохранитель пропустил удаление.
"""
import fcntl
import json
import os
import re
import sqlite3
import sys
import time
from collections import Counter
from contextlib import closing

# The production cron runs this file directly, while tests load it by path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from car_titles import extract_title, normalize_brand
from collector.registration_age import customs_registration_bounds, registration_month

SQLITE_PATH = os.environ.get("SQLITE_PATH", "/srv/che168/cars.db")
PG_DSN = os.environ.get(
    "IMPORT_PG_DSN", "postgresql://postgres@/avtopodborimport?host=/var/run/postgresql"
)
LOCK_PATH = "/tmp/import_cars.lock"
# Дата копии, которую уже перенесли (домашняя папка postgres)
STATE_PATH = os.environ.get("IMPORT_STATE", "/var/lib/postgresql/import_cars.last")
SOLD_DELETE_BLOCKED = "sold-delete-blocked"
SOLD_DELETE_BLOCKED_EXIT = 3
BATCH = 1000
SOURCE_PHOTO_URL = re.compile(r"""https://(?:[0-9a-z-]+\.)+autoimg\.cn/[^\s"'\\]+""")

# Столбцы машин: одинаковые имена в базе сборщика и в базе сайта.
# local_photo, local_photo_2, local_photo_3 и local_photo_4 есть только на сайте — импорт их не трогает.
CAR_COLS = [
    "listing_id", "url", "brand_ru", "brand_cn", "model", "year", "mileage_km",
    "price_cny", "price_wan", "gearbox", "fuel", "color", "city", "description", "images",
    "series_name", "spec_id", "province_id", "displacement", "environmental",
    "first_reg_date", "dealer_id", "dealer_name", "publish_date", "is_active",
    "details_json", "drive", "params_text", "power_hp", "engine_ml", "photos", "photo_count",
    "tires", "scraped_at", "updated_at",
]
CAR_DERIVED_COLS = ["reg_month", "brand_id", "model_name", "model_slug", "trim"]
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
        if c == "reg_month":
            sets.append("reg_month = car_registration_month("
                        "COALESCE(EXCLUDED.first_reg_date, cars.first_reg_date), "
                        "COALESCE(EXCLUDED.year, cars.year))")
        elif c in CAR_EXACT or c in CAR_DERIVED_COLS:
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


def normalize_photo_links(images):
    """Wrap a single Che168 cover URL while preserving existing image lists."""
    if isinstance(images, str):
        url = images.strip()
        if SOURCE_PHOTO_URL.fullmatch(url):
            return json.dumps([url])
    return images


def normalize_saved_photo_links(dry_run):
    import psycopg2

    with psycopg2.connect(PG_DSN) as pg, pg.cursor() as cur:
        cur.execute("""
            SELECT listing_id, images FROM cars
            WHERE is_active = 1 AND local_photo IS NULL
              AND NOT pg_input_is_valid(images, 'json')
        """)
        changes = []
        for listing_id, images in cur:
            normalized = normalize_photo_links(images)
            if normalized != images:
                changes.append((normalized, listing_id, images))
        if not dry_run and changes:
            cur.executemany(
                """UPDATE cars SET images = %s
                   WHERE listing_id = %s AND images = %s AND is_active = 1
                     AND local_photo IS NULL""",
                changes,
            )
        count = len(changes) if dry_run or not changes else cur.rowcount
    print(f"{'К исправлению' if dry_run else 'Исправлено'} одиночных ссылок на фото: {count}")


def enrich_car(row, brands, models, unknown):
    data = dict(zip(CAR_COLS, row))
    data["images"] = normalize_photo_links(data["images"])
    imported = tuple(data.values()) + (registration_month(data["first_reg_date"], data["year"]),)
    raw_brand = (data["brand_ru"] or data["brand_cn"] or "").strip()
    found = brands.get(normalize_brand(raw_brand))
    if not found and data["brand_cn"]:
        found = brands.get(normalize_brand(data["brand_cn"]))
    if not found:
        if raw_brand:
            unknown[raw_brand] += 1
        return imported + (None, None, None, None)
    brand_id, slug = found
    name, model_slug, trim = extract_title(
        data["model"] or "", data["series_name"], data["brand_cn"], models.get(slug, {}), slug
    )
    return imported + (brand_id, name, model_slug, trim)


def copy_table(sq, cur, sql, src_cols, table, title_catalog=None, active_only=False, excluded_ids=()):
    from psycopg2.extras import execute_values
    condition = " WHERE is_active=1" if active_only else ""
    rows = sq.execute(f"SELECT {', '.join(src_cols)} FROM {table}{condition}")
    total = 0
    unknown = Counter()
    listing_index = src_cols.index("listing_id") if excluded_ids else None
    while True:
        batch = rows.fetchmany(BATCH)
        if not batch:
            break
        if listing_index is not None:
            batch = [row for row in batch if str(row[listing_index]) not in excluded_ids]
            if not batch:
                continue
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


def registration_cleanup_plan(sq, cur):
    """Use the same PostgreSQL calendar date as the catalog."""
    cur.execute("SELECT current_date")
    oldest, _ = customs_registration_bounds(cur.fetchone()[0])
    incoming = {}
    source_aged = set()
    for listing_id, first_reg, year in sq.execute(
        "SELECT listing_id,first_reg_date,year FROM cars WHERE is_active=1"
    ):
        listing_id = str(listing_id)
        incoming[listing_id] = (first_reg, year)
        month = registration_month(first_reg, year)
        if month is not None and month <= oldest:
            source_aged.add(listing_id)

    cur.execute("SELECT listing_id::text,reg_month,first_reg_date,year FROM cars")
    site_aged = set()
    for listing_id, month, first_reg, year in cur:
        if listing_id in incoming and listing_id not in source_aged:
            # Match the upsert: prefer corrected registration data while retaining
            # previously known fields when the snapshot supplies NULL.
            new_first_reg, new_year = incoming[listing_id]
            month = registration_month(new_first_reg if new_first_reg is not None else first_reg,
                                       new_year if new_year is not None else year)
        if listing_id in source_aged or (month is not None and month <= oldest):
            site_aged.add(listing_id)
    return oldest, source_aged, site_aged


def main():
    with open(LOCK_PATH, "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit("импорт уже идёт — пропуск")
        return run_import()


def run_import():
    dry = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    allow_mass_delete = "--allow-mass-delete" in sys.argv
    published = "--published" in sys.argv

    if "--normalize-photo-links" in sys.argv:
        normalize_saved_photo_links(dry)
        return

    t0 = time.time()
    sq, source_stat, identity = open_source(published=published)
    n_cars, n_active = sq.execute(
        "SELECT count(*), sum(is_active = 1 AND price_cny > 0) FROM cars").fetchone()
    n_specs = sq.execute("SELECT count(*) FROM specs").fetchone()[0]
    stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(source_stat.st_mtime))
    print(f"{time.strftime('%Y-%m-%d %H:%M')} источник {SQLITE_PATH} от {stamp}: "
          f"машин {n_cars} (в продаже с ценой {n_active}), комплектаций {n_specs}")
    if not n_cars or not n_active:
        sq.close()
        sys.exit("пустая копия или нет активных машин — импорт и удаление отменены")

    if dry:
        import psycopg2
        with closing(sq), closing(psycopg2.connect(PG_DSN)) as pg:
            pg.set_session(readonly=True)
            with pg, pg.cursor() as cur:
                oldest, source_aged, site_aged = registration_cleanup_plan(sq, cur)
        print(f"План по возрасту (месяц регистрации ≤ {oldest}): исключить из копии "
              f"{len(source_aged)}, удалить с сайта {len(site_aged)}")
        print("проверка источника: ok, в базу сайта ничего не записано")
        return

    try:
        with open(STATE_PATH) as state:
            last, _, last_result = state.read().strip().partition("\n")
    except OSError:
        last = last_result = ""
    if last == identity and not (force or allow_mass_delete):
        sq.close()
        if last_result == SOLD_DELETE_BLOCKED:
            print("ПРЕДОХРАНИТЕЛЬ: эта копия уже импортирована с пропуском удаления")
            return SOLD_DELETE_BLOCKED_EXIT
        print("копия не менялась с прошлого импорта — пропуск")
        return

    import psycopg2
    from sold_cars import remove_aged_out, remove_confirmed
    pg = psycopg2.connect(PG_DSN)
    try:
        with pg, pg.cursor() as cur:  # одна транзакция: сайт видит либо старые данные, либо новые
            oldest, source_aged, site_aged = registration_cleanup_plan(sq, cur)
            removed = remove_confirmed(sq, cur, allow_mass_delete=allow_mass_delete, aged_out_ids=site_aged)
            aged_removed = remove_aged_out(cur, site_aged)
            title_catalog = load_title_catalog(cur)
            s = copy_table(sq, cur, spec_upsert_sql(), SPEC_SRC, "specs")
            c = copy_table(sq, cur, car_upsert_sql(), CAR_COLS, "cars", title_catalog,
                           active_only=True, excluded_ids=source_aged | site_aged)
            cur.execute("SELECT count(*), count(*) FILTER (WHERE is_active = 1 AND price_cny > 0) FROM cars")
            site_total, site_active = cur.fetchone()
    finally:
        pg.close()
        sq.close()
    print(f"Удалено по возрасту: {aged_removed} (месяц регистрации ≤ {oldest}); "
          f"исключено из копии: {len(source_aged)}", flush=True)
    from refresh_catalog_queue import main as refresh_catalog_queue
    refresh_catalog_queue()
    temporary_state = STATE_PATH + ".tmp"
    with open(temporary_state, "w") as f:
        result = SOLD_DELETE_BLOCKED + "\n" if removed is None else ""
        f.write(identity + "\n" + result)
    os.replace(temporary_state, STATE_PATH)
    deletion = "удаление снятых пропущено" if removed is None else f"удалено снятых {removed}"
    print(f"готово за {time.time() - t0:.0f} с: комплектаций {s}, машин {c}; "
          f"на сайте машин {site_total}, в продаже с ценой {site_active}; {deletion}")
    return SOLD_DELETE_BLOCKED_EXIT if removed is None else 0


if __name__ == "__main__":
    sys.exit(main())
