#!/bin/sh
# Keep space for the database and application while backfilling photos.
set -eu
if /usr/bin/python3 -c 'import sys; sys.path.insert(0,"/opt/avtopodborimport"); from photo_relay import workstation_alive; sys.exit(0 if workstation_alive() else 1)'; then
    echo "Workstation bridge active; direct photo downloader skipped"
    exit 0
fi
available_kb=$(df -Pk /opt/avtopodborimport/photos | awk 'NR == 2 {print $4}')
if [ "$available_kb" -lt 4194304 ]; then
    echo "Photo batch skipped: less than 4 GiB free"
    exit 0
fi
exec /usr/bin/python3 /opt/avtopodborimport/fetch_photos.py --limit 2000 --minutes 40
