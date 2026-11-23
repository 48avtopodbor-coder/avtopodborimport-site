#!/bin/sh
# Keep the existing hourly schedule; let the workstation carry the start request.
set -eu
avto_state=/srv/che168/pc-bridge
mkdir -p "$avto_state"
exec 9>"$avto_state/collect.lock"
flock -x 9
avto_pending="$avto_state/collect-request.$$"
date +%s%N > "$avto_pending"
mv -f "$avto_pending" "$avto_state/collect-request"
flock -u 9
exec 9>&-
if /usr/bin/python3 -c 'import sys; sys.path.insert(0,"/opt/avtopodborimport"); from photo_relay import workstation_alive; sys.exit(0 if workstation_alive() else 1)'; then
    echo "$(date '+%Y-%m-%d %H:%M') запуск сборщика передан компьютеру"
    exit 0
fi
exec sh /srv/che168/trigger.direct.sh
