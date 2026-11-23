#!/usr/bin/env python3
"""Generate reviewable OSM/OSRM road distances for missing cities, never on page load."""

import argparse
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def request(url):
    time.sleep(1)
    with urlopen(
        Request(url, headers={"User-Agent": "AvtopodborCatalog/1.0"}), timeout=25
    ) as response:
        return json.load(response)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("terms", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    entries = json.loads(a.terms.read_text())["entries"]
    done = json.loads(a.output.read_text()) if a.output.exists() else {}
    for row in entries:
        if row["kind"] != "city" or row["source"] in done:
            continue
        city = row["source"]
        try:
            geo = request(
                "https://photon.komoot.io/api/?"
                + urlencode(
                    {
                        "q": row.get("geocode_query", city),
                        "osm_tag": "place",
                        "limit": 5,
                        "lang": "en",
                    }
                )
            )
            candidates = [
                f
                for f in geo["features"]
                if f["properties"].get("countrycode") == "CN"
                and f["properties"].get("osm_value") in ("city",)
            ]
            if row.get("expected_state"):
                candidates = [
                    f
                    for f in candidates
                    if f["properties"].get("state") == row["expected_state"]
                ]
            if not candidates:
                print("No unambiguous city:", city, flush=True)
                continue
            feature = candidates[0]
            lon, lat = feature["geometry"]["coordinates"]
            route_url = f"https://router.project-osrm.org/route/v1/driving/{lon},{lat};80.418,44.217?overview=false"
            route = request(route_url)
            if route.get("code") != "Ok":
                raise ValueError("No route")
            meters = route["routes"][0]["distance"]
            if not 1000 < meters < 10000000:
                raise ValueError("Unexpected route length")
            done[city] = {
                "city_ru": row["name"],
                "coordinates": [lon, lat],
                "geocoder": feature["properties"],
                "distance_km": round(meters / 1000),
                "route_url": route_url,
                "attribution": "© OpenStreetMap contributors; OSRM driving route; city centre to Khorgos, approximate",
            }
            a.output.write_text(json.dumps(done, ensure_ascii=False, indent=2) + "\n")
            print(
                city,
                row["name"],
                round(meters / 1000),
                feature["properties"]["name"],
                flush=True,
            )
        except Exception as e:
            print(city, type(e).__name__, str(e), flush=True)


if __name__ == "__main__":
    main()
