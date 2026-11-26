#!/bin/sh
# run_daily.sh — сбор по расписанию (cron): список машин -> проверка проданных -> цвет, фото и характеристики новых.
# Если предыдущий запуск ещё идёт, этот сразу пропускается (flock).
cd /home/c/cc14862/che168 || exit 1
PY=/home/c/cc14862/che168/.venv/bin/python
if [ -f data/cron.log ] && [ "$(stat -c %s data/cron.log)" -gt 20000000 ]; then
    mv data/cron.log data/cron.log.old
fi
echo "--- $(date '+%Y-%m-%d %H:%M') запуск по расписанию" >> data/cron.log
exec /usr/bin/flock -n data/.lock sh -c "$PY scraper.py --no-details && $PY enrich.py --recheck && $PY details.py" >> data/cron.log 2>&1
