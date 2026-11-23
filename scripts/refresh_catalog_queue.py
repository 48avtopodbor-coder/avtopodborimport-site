#!/usr/bin/env python3
"""Collect unknown catalog terms after every import; never guess a translation."""

import os
import psycopg2
from car_titles import source_series
from psycopg2.extras import execute_values
from collections import Counter


def main():
    with psycopg2.connect(
        os.environ.get("IMPORT_PG_DSN", "dbname=avtopodborimport user=postgres")
    ) as con:
        with con.cursor() as cur:
            cur.execute(
                "SELECT c.brand_ru,b.slug,c.model,c.series_name,c.city,c.brand_id,c.model_name,t.city_cn FROM cars c LEFT JOIN brands b ON b.id=c.brand_id LEFT JOIN city_translations t ON t.city_cn=c.city WHERE c.is_active=1 AND c.price_cny>0"
            )
            terms = Counter()
            for brand, slug, model, series, city, brand_id, model_name, city_cn in cur:
                if not brand_id and brand:
                    terms[("brand", "", brand)] += 1
                if brand_id and not model_name:
                    term = source_series(model or "", series) or model
                    if term:
                        terms[("model", slug, term)] += 1
                if city and city_cn is None:
                    terms[("city", "", city)] += 1
            cur.execute("UPDATE catalog_translation_queue SET cars_count=0")
            if terms:
                execute_values(
                    cur,
                    """INSERT INTO catalog_translation_queue(kind,scope,source_text,cars_count) VALUES %s
                ON CONFLICT(kind,scope,source_text) DO UPDATE SET cars_count=excluded.cars_count,status='pending',last_seen=now()""",
                    [(*key, n) for key, n in terms.items()],
                )
            cur.execute(
                "UPDATE catalog_translation_queue SET status='applied' WHERE cars_count=0"
            )
            print("Unknown catalog terms:", len(terms))


if __name__ == "__main__":
    main()
