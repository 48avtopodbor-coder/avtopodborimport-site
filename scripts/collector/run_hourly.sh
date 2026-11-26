#!/bin/sh
# Запуск сборщика che168 по расписанию — раз в час, командой с нового сервера (ssh hosting ...).
# Если прошлый запуск ещё идёт — этот пропускается. Весь вывод — в data/cron.log.
cd /home/c/cc14862/che168 || exit 1
if [ -f data/cron.log ] && [ "$(stat -c %s data/cron.log)" -gt 20000000 ]; then
    mv data/cron.log data/cron.log.old
fi
/usr/bin/flock -n -E 75 data/.lock /bin/sh hourly_job.sh >> data/cron.log 2>&1
if [ $? -eq 75 ]; then
    echo "$(date '+%Y-%m-%d %H:%M') прошлый запуск ещё идёт — пропуск" >> data/cron.log
fi
