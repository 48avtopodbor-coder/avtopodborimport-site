#!/bin/sh
# Одна порция работы сборщика che168 (запускает run_hourly.sh, под замком).
#  1) Раз в 11 часов — проход по списку: новые машины, цены, проданные (около 1,5 часа).
#     После него — перепроверка машин, которых давно нет в списке (продана или нет).
#  2) Каждый раз — цвет, фото и характеристики машин, у которых их ещё нет (до 50 минут).
cd /home/c/cc14862/che168 || exit 1
PY=/home/c/cc14862/che168/.venv/bin/python
echo "=== $(date '+%Y-%m-%d %H:%M') запуск по расписанию"
list_rc=0
recheck_rc=0
details_rc=0
$PY scraper.py --no-details --every 660 || list_rc=$?
if [ "$list_rc" -eq 0 ]; then
    $PY enrich.py --recheck || recheck_rc=$?
fi
$PY details.py --minutes 50 || details_rc=$?
# The collector returns 10 when a full list pass is not due yet.
if { [ "$list_rc" -ne 0 ] && [ "$list_rc" -ne 10 ]; } || [ "$recheck_rc" -ne 0 ] || [ "$details_rc" -ne 0 ]; then
    echo "=== $(date '+%Y-%m-%d %H:%M') ошибка: список=$list_rc перепроверка=$recheck_rc карточки=$details_rc"
    exit 1
fi
echo "=== $(date '+%Y-%m-%d %H:%M') готово (список=$list_rc перепроверка=$recheck_rc карточки=$details_rc)"
