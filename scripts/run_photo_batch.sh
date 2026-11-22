#!/bin/sh
# Keep space for the database and application while backfilling photos.
set -eu
available_kb=$(df -Pk /opt/avtopodborimport/photos | awk 'NR == 2 {print $4}')
if [ "$available_kb" -lt 4194304 ]; then
    echo "Photo batch skipped: less than 4 GiB free"
    exit 0
fi
exec /usr/bin/python3 /opt/avtopodborimport/fetch_photos.py --limit 2000 --minutes 40
