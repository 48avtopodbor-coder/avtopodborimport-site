#!/bin/sh
# После обновления файлов: остановить идущий сборщик и сразу запустить новую версию.
cd /home/c/cc14862/che168 || exit 1
chmod +x run_hourly.sh hourly_job.sh
echo "--- файлы:"
md5sum che168_api.py scraper.py details.py enrich.py run_hourly.sh hourly_job.sh | cut -c1-8,33-
if pkill -f 'scraper\.py|details\.py|enrich\.py'; then
    sleep 3
    echo "--- старый запуск остановлен"
fi
pgrep -af 'scraper\.py|details\.py|enrich\.py' && echo "!!! что-то из сборщика ещё работает"
setsid nohup sh run_hourly.sh >/dev/null 2>&1 </dev/null &
echo "--- новый запуск начат, через 30 секунд покажу журнал:"
sleep 30
tail -6 data/cron.log
