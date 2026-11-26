#!/bin/sh
# Публикует проверенный снимок и запускает его импорт: 04:05 и 16:05 МСК, root cron.
set -eu

cd /srv/che168
exec 9>/srv/che168/pull.lock
flock -n 9 || { echo "копирование уже идёт"; exit 1; }

temporary=$(mktemp /srv/che168/cars.db.download.XXXXXXXX)
snapshot=$(mktemp /srv/che168/cars.db.snapshot.XXXXXXXX)
previous=$(mktemp /srv/che168/cars.db.previous.XXXXXXXX)
cleanup() {
  rm -f "$temporary" "$snapshot" "$previous"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

echo "--- $(date '+%Y-%m-%d %H:%M') копия базы"
ssh -o BatchMode=yes hosting 'sh /home/c/cc14862/che168/backup.sh'
ssh -C -o BatchMode=yes hosting 'cat /home/c/cc14862/che168/data/cars_backup.db' > "$temporary"
python3 - "$temporary" <<'PY'
import sqlite3
import sys

connection = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
try:
    result = connection.execute("PRAGMA quick_check").fetchone()[0]
    count = connection.execute("SELECT COUNT(*) FROM cars").fetchone()[0]
    connection.execute("SELECT COUNT(*) FROM specs").fetchone()
    print("проверка копии:", result, "| машин:", count)
    if result != "ok":
        raise SystemExit(1)
finally:
    connection.close()
PY
chmod 644 "$temporary"

# Снимок и опубликованный файл указывают на одни и те же проверенные данные.
rm "$snapshot"
ln "$temporary" "$snapshot"
if [ -f cars.db ]; then
  rm "$previous"
  ln cars.db "$previous"
  mv -f "$previous" cars.db.prev
fi
mv -f "$temporary" cars.db
ls -lh cars.db | awk '{print "готово:", $5, $9}'

# Почасовой запуск остаётся повторной попыткой, если этот импорт не прошёл.
import_status=0
sudo -u postgres env SQLITE_PATH="$snapshot" \
  python3 /opt/avtopodborimport/import_cars.py --published || import_status=$?

if [ "$import_status" -eq 0 ]; then
  # Both daily imports clean files; the timer retries when a photo batch owns the lock.
  python3 /opt/avtopodborimport/cleanup_sold_photos.py --apply
  if ! ssh -o BatchMode=yes -o ConnectTimeout=15 hosting \
    'cd /home/c/cc14862/che168 && python3 cleanup_collector_photos.py --apply'; then
    echo "очистка старых фото сборщика не прошла; повтор при следующей копии"
  fi
elif [ "$import_status" -ne 3 ]; then
  exit "$import_status"
fi

if [ -f /opt/avtopodborimport/translate_seller_descriptions.py ] && \
   [ -f /opt/avtopodborimport/seller-dictionary.json ]; then
  nohup nice -n 15 sudo -u postgres python3 \
    /opt/avtopodborimport/translate_seller_descriptions.py --limit 2000 \
    >> /srv/che168/translation.log 2>&1 < /dev/null 9>&- &
fi

# Keep a read-only report of electric model names and rated range.
if ! sh /opt/avtopodborimport/run_electric_catalog_audit.sh; then
  echo "проверка электромобилей завершилась с ошибками; см. отчёт electric-catalog-audit.json"
fi
exit "$import_status"
