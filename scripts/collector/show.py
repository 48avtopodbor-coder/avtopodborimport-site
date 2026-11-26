"""
show.py — последние машины с данными и сводка по базе.
Запуск: python3 show.py        (5 машин)
        python3 show.py 20     (20 машин)
"""
import sys

from database import get_conn, get_stats

n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
with get_conn() as conn:
    rows = conn.execute(
        "SELECT listing_id, brand_ru, model, year, first_reg_date, price_wan, mileage_km, color, gearbox, "
        "fuel, drive, power_hp, tires, photo_count, length(description) AS descr FROM cars "
        "WHERE params_at IS NOT NULL AND is_active = 1 ORDER BY params_at DESC LIMIT ?", (n,)).fetchall()
    specs = conn.execute("SELECT COUNT(*) FROM specs").fetchone()[0]
    photos = conn.execute("SELECT COUNT(*) FROM cars WHERE is_active = 1 AND photo_count > 0").fetchone()[0]
for r in rows:
    print("{} | {} {} | {} ({}) | {} 万 | {} км | {} | {} | {} | {} | {} л.с. | шины {} | фото {} | описание {} симв.".format(
        r["listing_id"], r["brand_ru"], (r["model"] or "")[:28], r["year"], r["first_reg_date"] or "?",
        r["price_wan"], r["mileage_km"], r["color"], r["gearbox"], r["fuel"], r["drive"], r["power_hp"],
        r["tires"] or "?", r["photo_count"] or 0, r["descr"] or 0))
st = get_stats()
print("В базе {} машин: продаётся {}, с данными {}, с фото {} | комплектаций {}".format(
    st["total"], st["active"], st["with_params"], photos, specs))
print("   " + " | ".join("{} {}".format(b, c) for b, c in st["by_brand"]))
