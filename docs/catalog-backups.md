# Резервные копии каталога

Сервер сайта каждый день в 05:30 МСК сохраняет два архива. Таймер `avto-catalog-backup.timer` запускается и после пропуска времени из-за выключения сервера. Для передачи используется существующее прямое SSH-подключение `hosting`. Компьютер владельца в передаче не участвует.

| Что можно восстановить | Где лежат копии |
|---|---|
| PostgreSQL сайта целиком, включая переводы, справочники и объявления | На сервере сборщика в `~/avto-private-backups/postgres/YYYY-MM-DD.dump` |
| Опубликованный снимок SQLite сборщика, включая `cars` и `specs` | На сервере сайта в `/var/backups/avtopodbor-catalog/YYYY-MM-DD.sqlite.zst` |

Копия SQLite берётся после утренней передачи в 04:05 МСК. Скрипт берёт общий замок публикации, проверяет `PRAGMA quick_check` и затем проверяет целостность архива Zstandard. В PostgreSQL используется согласованный снимок `pg_dump` в формате custom. Перед публикацией проверяется наличие записей данных для критических таблиц в оглавлении, а на принимающем сервере сверяется SHA-256. Каталоги закрыты правами 700, файлы — 600. Архивы появляются под итоговым именем через атомарное переименование.

Хранятся последние семь успешных дат. Повторный запуск за день заменяет копию этой даты. При перерыве в работе прежние успешные копии сохраняются до пополнения истории. Ориентир первого замера для семи дат — 406 МиБ на сервере сборщика и 540 МиБ на сервере сайта, плюс место под один временный архив. Фотографии хранятся отдельно от баз.

Ежечасная проверка места на обоих серверах и расчёт на декабрь описаны в [контроле места каталога](catalog-disk-space.md).

## Установка и проверка расписания

На сервере сайта от root из корня проверенной версии репозитория выполнить

```bash
install -m 755 scripts/backup_catalog.sh /opt/avtopodborimport/backup_catalog.sh
install -m 644 scripts/deploy/avto-catalog-backup.{service,timer} /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now avto-catalog-backup.timer
systemctl start avto-catalog-backup.service
systemctl list-timers avto-catalog-backup.timer
journalctl -u avto-catalog-backup.service --since '7 days ago'
```

## Пробное восстановление

Выбрать существующую дату архива и выполнить от root на сервере сайта. Команды создают отдельную пустую базу с уникальным именем, проверяют чтение основных таблиц и удаляют созданную проверочную базу при выходе. Для восстановления SQLite требуется свободное место под распакованный файл.

```bash
#!/usr/bin/env bash
set -euo pipefail
umask 077
day=2026-11-27
scratch=$(mktemp -d)
test_db=avto_restore_$(date +%s)_$$
made=0
cleanup() {
    if [ "$made" = 1 ]; then sudo -u postgres dropdb "$test_db"; fi
    rm -rf -- "$scratch"
}
trap cleanup EXIT
ssh -n -o BatchMode=yes hosting "cat ~/avto-private-backups/postgres/$day.dump" > "$scratch/catalog.dump"
sha256sum "$scratch/catalog.dump"
sudo -u postgres createdb -T template0 "$test_db"
made=1
sudo -u postgres pg_restore --exit-on-error --single-transaction --no-owner --no-privileges \
    -d "$test_db" < "$scratch/catalog.dump"
for tbl in seller_description_translations brands brand_aliases model_aliases city_translations cars; do
    sudo -u postgres psql -XAtq -v ON_ERROR_STOP=1 -d "$test_db" -c "SELECT '$tbl', count(*) FROM $tbl"
done
zstd -dqc "/var/backups/avtopodbor-catalog/$day.sqlite.zst" > "$scratch/collector.db"
python3 - "$scratch/collector.db" <<'PY'
import sqlite3
import sys
with sqlite3.connect("file:" + sys.argv[1] + "?mode=ro", uri=True) as db:
    assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
    print(db.execute("SELECT count(*) FROM cars").fetchone())
    print(db.execute("SELECT count(*) FROM specs").fetchone())
PY
```

27 ноября 2026 года файл архива PostgreSQL получен обратно с сервера сборщика, SHA-256 совпал с журналом отправки. В отдельной восстановленной базе число записей совпало с секциями COPY самого архива во всех шести проверенных таблицах.

| Таблица | Записей |
|---|---:|
| seller_description_translations | 32 273 |
| brands | 21 |
| brand_aliases | 44 |
| model_aliases | 419 |
| city_translations | 299 |
| cars | 46 455 |

Восстановленная SQLite прошла полный `integrity_check`. В ней 93 133 объявления и 5 129 комплектаций. Первые архивы занимали 60 796 480 и 80 959 847 байт соответственно.
