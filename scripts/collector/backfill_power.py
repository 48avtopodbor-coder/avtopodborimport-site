#!/usr/bin/env python3
"""Recalculate power from saved model specifications without API requests."""

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3

from config import DB_PATH
from power import ELECTRIFIED_FUELS, electrified_power_hp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    mode = "rw" if args.apply else "ro"
    uri = f"{Path(DB_PATH).resolve().as_uri()}?mode={mode}"
    expected, spec_updates = {}, []
    unresolved = cars = active_cards = 0
    with closing(sqlite3.connect(uri, uri=True, timeout=60)) as con, con:
        con.execute("BEGIN IMMEDIATE" if args.apply else "BEGIN")
        for spec_id, fuel, params_json, current in con.execute(
            "SELECT spec_id, fuel, params_json, power_hp FROM specs WHERE fuel IS NOT NULL",
        ):
            if fuel.strip().casefold() not in ELECTRIFIED_FUELS:
                continue
            corrected = electrified_power_hp(params_json, fuel)
            if corrected is None:
                unresolved += 1
                continue
            expected[spec_id] = corrected
            if corrected != current:
                spec_updates.append((corrected, spec_id))

        car_updates = set()
        for spec_id, current, count, active in con.execute("""
            SELECT spec_id, power_hp, count(*), count(CASE WHEN is_active = 1 AND price_cny > 0 THEN 1 END)
            FROM cars WHERE spec_id IS NOT NULL GROUP BY spec_id, power_hp
        """):
            corrected = expected.get(spec_id)
            if corrected is not None and current != corrected:
                car_updates.add((corrected, spec_id, corrected))
                cars += count
                active_cards += active
        if args.apply:
            con.executemany("UPDATE specs SET power_hp = ? WHERE spec_id = ?", spec_updates)
            con.executemany("UPDATE cars SET power_hp = ? WHERE spec_id = ? AND power_hp IS NOT ?", car_updates)

    print(json.dumps({"applied": args.apply, "specs": len(spec_updates), "cars": cars,
                      "active_cards": active_cards, "unresolved_specs": unresolved}))


if __name__ == "__main__":
    main()
