# database.py — работа с SQLite (встроенный модуль, без доп. зависимостей)

import sqlite3
import os
from config import DB_PATH
from loguru import logger

os.makedirs("data", exist_ok=True)

# Столбцы, добавленные после первой версии
EXTRA_COLUMNS = {
    "series_name":    "TEXT",
    "spec_id":        "TEXT",
    "province_id":    "TEXT",
    "displacement":   "TEXT",
    "environmental":  "TEXT",
    "first_reg_date": "TEXT",
    "dealer_id":      "TEXT",
    "dealer_name":    "TEXT",
    "publish_date":   "TEXT",
    "is_active":      "INTEGER DEFAULT 1",
    "details_json":   "TEXT",
    "enriched_at":    "TIMESTAMP",
    "drive":          "TEXT",
    "params_text":    "TEXT",
    "params_at":      "TIMESTAMP",
    "power_hp":       "INTEGER",
    "engine_ml":      "INTEGER",
    "seen_at":        "TIMESTAMP",   # когда машина последний раз была в списке che168
    "photos":         "TEXT",        # ссылки на все фото, JSON-список
    "photo_count":    "INTEGER",
    "tires":          "TEXT",        # размер шин, например 245/45 R18
}
SPEC_COLUMNS = {"tires": "TEXT", "full": "INTEGER"}   # добавлены после первой версии таблицы specs

# Что можно записать при добавлении машины
CAR_COLUMNS = ("listing_id", "url", "brand_ru", "brand_cn", "model", "year", "mileage_km",
               "price_cny", "price_wan", "gearbox", "fuel", "color", "city", "description", "images",
               "raw_data", "series_name", "spec_id", "province_id", "displacement", "environmental",
               "first_reg_date", "dealer_id", "dealer_name", "publish_date")


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создаёт таблицы, если их нет, и добавляет недостающие столбцы."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cars (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id  TEXT UNIQUE,
                url         TEXT,
                brand_ru    TEXT,
                brand_cn    TEXT,
                model       TEXT,
                year        INTEGER,
                mileage_km  INTEGER,
                price_cny   REAL,
                price_wan   REAL,
                gearbox     TEXT,
                fuel        TEXT,
                color       TEXT,
                city        TEXT,
                description TEXT,
                images      TEXT,
                raw_data    TEXT,
                scraped_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        existing = {r[1] for r in conn.execute("PRAGMA table_info(cars)")}
        for col, typ in EXTRA_COLUMNS.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE cars ADD COLUMN {col} {typ}")
                logger.info("В таблицу добавлен столбец {}", col)
        # Параметры комплектаций: у всех машин одной комплектации они одинаковые
        conn.execute("""
            CREATE TABLE IF NOT EXISTS specs (
                spec_id     TEXT PRIMARY KEY,
                fuel        TEXT,
                drive       TEXT,
                gearbox     TEXT,
                power_hp    INTEGER,
                engine_ml   INTEGER,
                params_text TEXT,
                params_json TEXT,
                fetched_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        have = {r[1] for r in conn.execute("PRAGMA table_info(specs)")}
        for col, typ in SPEC_COLUMNS.items():
            if col not in have:
                conn.execute(f"ALTER TABLE specs ADD COLUMN {col} {typ}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_brand ON cars(brand_ru)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_year  ON cars(year)")
        conn.commit()
    logger.info("БД инициализирована: {}", DB_PATH)


def save_cars(cars: list) -> int:
    """Сохраняет пачку машин: новые добавляет, известным обновляет цену, пробег и «видели сейчас».
    Возвращает, сколько машин новых."""
    new = 0
    with get_conn() as conn:
        for car in cars:
            cur = conn.execute("""
                UPDATE cars SET price_cny=COALESCE(?, price_cny), price_wan=COALESCE(?, price_wan),
                       mileage_km=COALESCE(?, mileage_km), is_active=1,
                       seen_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
                WHERE listing_id=?
            """, (car.get("price_cny"), car.get("price_wan"), car.get("mileage_km"), car["listing_id"]))
            if cur.rowcount:
                continue
            cols = [c for c in CAR_COLUMNS if car.get(c) is not None]
            conn.execute("INSERT INTO cars ({}, seen_at) VALUES ({}, CURRENT_TIMESTAMP)".format(
                ", ".join(cols), ", ".join(["?"] * len(cols))), [car[c] for c in cols])
            new += 1
        conn.commit()
    return new


def save_car(car: dict) -> bool:
    """Сохраняет одну машину. True = новая."""
    return save_cars([car]) == 1


def cars_to_enrich(limit=None) -> list:
    """listing_id машин, по которым ещё не догружены подробности."""
    sql = "SELECT listing_id FROM cars WHERE enriched_at IS NULL AND is_active = 1 ORDER BY id"
    params = ()
    if limit:
        sql += " LIMIT ?"
        params = (limit,)
    with get_conn() as conn:
        return [r[0] for r in conn.execute(sql, params)]


def update_details(listing_id: str, fields: dict):
    """Записывает подробности по машине и отмечает время догрузки."""
    cols = ", ".join(f"{k}=?" for k in fields)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE cars SET {cols}, enriched_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP "
            f"WHERE listing_id=?",
            (*fields.values(), listing_id),
        )
        conn.commit()


def get_stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM cars").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM cars WHERE is_active = 1").fetchone()[0]
        with_params = conn.execute(
            "SELECT COUNT(*) FROM cars WHERE is_active = 1 AND params_at IS NOT NULL").fetchone()[0]
        brands = conn.execute(
            "SELECT brand_ru, COUNT(*) FROM cars WHERE is_active = 1 GROUP BY brand_ru ORDER BY 2 DESC"
        ).fetchall()
    return {"total": total, "active": active, "with_params": with_params,
            "by_brand": [(r[0], r[1]) for r in brands]}
