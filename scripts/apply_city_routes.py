#!/usr/bin/env python3
"""Apply inspected route results without overwriting existing distance estimates."""

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("file", type=Path)
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    rows = json.loads(a.file.read_text())
    for city, row in rows.items():
        if (
            not 1 < row["distance_km"] < 10000
            or urlsplit(row["route_url"]).hostname != "router.project-osrm.org"
        ):
            raise ValueError("Invalid route: " + city)
        if (
            row["geocoder"].get("countrycode") != "CN"
            or row["geocoder"].get("osm_value") != "city"
        ):
            raise ValueError("Not a city: " + city)
    print("Validated road distances:", len(rows))
    if not a.apply:
        return
    import psycopg2

    with psycopg2.connect(
        os.environ.get("IMPORT_PG_DSN", "dbname=avtopodborimport user=postgres")
    ) as con:
        with con.cursor() as cur:
            for city, row in rows.items():
                cur.execute(
                    "UPDATE city_translations SET distance_km=%s, distance_source=%s WHERE city_cn=%s AND distance_km IS NULL",
                    (row["distance_km"], row["route_url"], city),
                )


if __name__ == "__main__":
    main()
