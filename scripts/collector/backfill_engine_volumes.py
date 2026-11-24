"""Restore missing engine volumes from saved explicit units; no network requests."""

import argparse
import json

from database import get_conn
from details import engine_ml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    repaired = cards = 0
    with get_conn() as con:
        rows = con.execute(
            'SELECT spec_id,params_json FROM specs WHERE (engine_ml IS NULL OR engine_ml=0) AND params_json IS NOT NULL'
        ).fetchall()
        for row in rows:
            try:
                params = {key: value for _, items in json.loads(row['params_json']) for key, value in items}
            except (ValueError, TypeError):
                continue
            volume = engine_ml(params)
            if volume is None:
                continue
            repaired += 1
            cards += con.execute(
                'SELECT count(*) FROM cars WHERE spec_id=? AND is_active=1 AND price_cny>0 AND (engine_ml IS NULL OR engine_ml=0)',
                (row['spec_id'],),
            ).fetchone()[0]
            if args.apply:
                con.execute('UPDATE specs SET engine_ml=? WHERE spec_id=? AND (engine_ml IS NULL OR engine_ml=0)', (volume, row['spec_id']))
                con.execute('UPDATE cars SET engine_ml=? WHERE spec_id=? AND (engine_ml IS NULL OR engine_ml=0)', (volume, row['spec_id']))
        if args.apply:
            con.commit()
    print(json.dumps({'applied': args.apply, 'specs': repaired, 'active_cards': cards}))


if __name__ == '__main__':
    main()
