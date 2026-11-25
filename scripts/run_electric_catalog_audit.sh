#!/bin/sh
# Called after imports and by the existing hourly translation worker; no new cron.
set -eu
report=/srv/che168/electric-catalog-audit.json
temporary=$(mktemp /srv/che168/electric-catalog-audit.XXXXXXXX)
trap 'rm -f "$temporary"' EXIT
status=0
nice -n 15 docker exec avtopodbor-web node --no-warnings --experimental-strip-types \
  /app/scripts/electric_catalog_audit.mjs > "$temporary" || status=$?
# Do not replace the last valid report with a failed/incomplete process output.
python3 - "$temporary" <<'PY'
import json,sys
with open(sys.argv[1]) as f:
    r=json.load(f)
for key in ('checked_at','cars','models','named','with_range','errors','warnings','issues'):
    if key not in r: raise SystemExit('неполный отчёт проверки электромобилей')
print('Проверка электричек:', r['cars'], '| без названия:', r['cars']-r['named'],
      '| без запаса хода:', r['cars']-r['with_range'], '| ошибок:', r['errors'], '| замечаний:', r['warnings'])
PY
chmod 644 "$temporary"
mv -f "$temporary" "$report"
exit "$status"
