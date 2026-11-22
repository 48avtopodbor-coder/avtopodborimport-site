#!/usr/bin/env python3
"""Populate new title fields without modifying the original cars.model."""

import os
from collections import Counter

import psycopg2
from psycopg2.extras import execute_values

from car_titles import extract_title, normalize_brand
from import_cars import load_title_catalog


def main():
    dsn = os.environ.get(
        "IMPORT_PG_DSN", "postgresql://postgres@/avtopodborimport?host=/var/run/postgresql"
    )
    pg = psycopg2.connect(dsn)
    counts = Counter()
    unknown = Counter()
    unresolved = Counter()
    with pg:
        with pg.cursor() as cur:
            brands, models = load_title_catalog(cur)
            cur.execute("SELECT listing_id, brand_ru, brand_cn, model, series_name FROM cars")
            rows = cur.fetchall()
            for start in range(0, len(rows), 1000):
                updates = []
                for listing_id, brand_ru, brand_cn, full_model, series in rows[start:start + 1000]:
                    raw_brand = (brand_ru or brand_cn or "").strip()
                    found = brands.get(normalize_brand(raw_brand)) or brands.get(normalize_brand(brand_cn))
                    if not found:
                        if raw_brand:
                            unknown[raw_brand] += 1
                        updates.append((listing_id, None, None, None, None))
                        continue
                    brand_id, slug = found
                    name, model_slug, trim = extract_title(
                        full_model or "", series, brand_cn, models.get(slug, {}), slug
                    )
                    if name:
                        counts[slug] += 1
                    else:
                        unresolved[(slug, series or full_model or "")] += 1
                    updates.append((listing_id, brand_id, name, model_slug, trim))
                execute_values(cur, """UPDATE cars AS c SET
                    brand_id = v.brand_id, model_name = v.model_name,
                    model_slug = v.model_slug, trim = v.trim
                    FROM (VALUES %s) AS v(listing_id, brand_id, model_name, model_slug, trim)
                    WHERE c.listing_id = v.listing_id""", updates, page_size=1000,
                    template="(%s::text,%s::integer,%s::text,%s::text,%s::text)")
            if unknown:
                execute_values(cur, """INSERT INTO unmapped_brand_names (raw_name, cars_count)
                    VALUES %s ON CONFLICT (raw_name) DO UPDATE SET
                    cars_count = EXCLUDED.cars_count, last_seen = now()""", list(unknown.items()))
    print(f"Обработано {len(rows)} машин; моделей сопоставлено {sum(counts.values())}")
    print("Без сопоставленной марки:", dict(unknown))
    print("Неизвестные серии (первые 50):")
    for (slug, source), count in unresolved.most_common(50):
        print(f"{slug}: {source} — {count}")
    pg.close()


if __name__ == "__main__":
    main()
