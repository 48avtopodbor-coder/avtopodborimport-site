"""Restore full source colour labels from saved car details, without API requests."""

import argparse
import json

from database import get_conn
from details import color_ru


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    changed = active = 0
    with get_conn() as con:
        rows = con.execute(
            'SELECT listing_id,color,details_json,is_active FROM cars WHERE details_json IS NOT NULL'
        ).fetchall()
        for row in rows:
            try:
                info = json.loads(row['details_json'])
            except (ValueError, TypeError):
                continue
            source = info.get('colorname') if isinstance(info, dict) else None
            if not isinstance(source, str) or not source.strip():
                continue
            label = color_ru(source)
            if label == row['color']:
                continue
            changed += 1
            active += bool(row['is_active'])
            if args.apply:
                con.execute(
                    'UPDATE cars SET color=? WHERE listing_id=? AND color IS ?',
                    (label, row['listing_id'], row['color']),
                )
        if args.apply:
            con.commit()
    print(json.dumps({'applied': args.apply, 'changed': changed, 'active': active}))


if __name__ == '__main__':
    main()
