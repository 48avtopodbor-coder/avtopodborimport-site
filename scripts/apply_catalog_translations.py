#!/usr/bin/env python3
"""Apply reviewed reusable catalog mappings, then refill existing titles and queue."""

import argparse
import json
import os
from pathlib import Path
import re
import psycopg2


def validate(entries):
    keys = set()
    for row in entries:
        key = (row["kind"], row.get("brand", ""), row["source"])
        if key in keys:
            raise ValueError("Duplicate source: " + str(key))
        keys.add(key)
        if (
            not row.get("reviewed")
            or not row["name"].strip()
            or re.search("[一-龥]", row["name"])
        ):
            raise ValueError("Unreviewed or incomplete: " + str(key))
        if row["kind"] in ("model", "brand"):
            if not re.fullmatch("[a-z0-9]+(?:-[a-z0-9]+)*", row["slug"]):
                raise ValueError("Invalid model slug")
        elif row["kind"] != "city":
            raise ValueError("Unsupported catalog kind")
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    rows = validate(json.loads(args.file.read_text())["entries"])
    print("Validated mappings:", len(rows))
    if not args.apply:
        return
    with psycopg2.connect(
        os.environ.get("IMPORT_PG_DSN", "dbname=avtopodborimport user=postgres")
    ) as con:
        with con.cursor() as cur:
            for row in rows:
                if row["kind"] == "city":
                    cur.execute(
                        "INSERT INTO city_translations(city_cn,city_ru) VALUES (%s,%s) ON CONFLICT(city_cn) DO UPDATE SET city_ru=excluded.city_ru",
                        (row["source"], row["name"]),
                    )
                elif row["kind"] == "brand":
                    from car_titles import normalize_brand

                    cur.execute(
                        "INSERT INTO brands(slug,name,name_cn) VALUES (%s,%s,%s) ON CONFLICT(slug) DO UPDATE SET name=excluded.name RETURNING id",
                        (row["slug"], row["name"], row["source"]),
                    )
                    brand_id = cur.fetchone()[0]
                    for alias in (row["source"], row["name"]):
                        cur.execute(
                            "SELECT brand_id FROM brand_aliases WHERE alias_norm=%s",
                            (normalize_brand(alias),),
                        )
                        existing = cur.fetchone()
                        if existing and existing[0] != brand_id:
                            raise ValueError(
                                "Brand alias belongs to another brand: " + alias
                            )
                        cur.execute(
                            "INSERT INTO brand_aliases(brand_id,alias_norm) VALUES (%s,%s) ON CONFLICT(alias_norm) DO NOTHING",
                            (brand_id, normalize_brand(alias)),
                        )
                else:
                    cur.execute("SELECT id FROM brands WHERE slug=%s", (row["brand"],))
                    brand = cur.fetchone()
                    if not brand:
                        raise ValueError("Unknown brand: " + row["brand"])
                    cur.execute(
                        """INSERT INTO model_aliases(brand_id,source_series,model_name,model_slug,source_url) VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT(brand_id,source_series) DO UPDATE SET model_name=excluded.model_name,model_slug=excluded.model_slug,source_url=excluded.source_url""",
                        (
                            brand[0],
                            row["source"],
                            row["name"],
                            row["slug"],
                            row.get("source_url", "https://www.che168.com/"),
                        ),
                    )
    from backfill_car_titles import main as backfill
    from refresh_catalog_queue import main as refresh

    backfill()
    refresh()


if __name__ == "__main__":
    main()
