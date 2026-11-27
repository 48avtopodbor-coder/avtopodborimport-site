#!/usr/bin/env bash
# PostgreSQL lives on the site; SQLite originates on the collector.
set -euo pipefail
umask 077

archive=/var/backups/avtopodbor-catalog
snapshot=/srv/che168/cars.db
day=$(date +%F)
install -d -m 700 "$archive"
exec 9>"$archive/.lock"
flock -n 9 || { echo "Резервное копирование уже запущено"; exit 1; }
scratch=$(mktemp -d "$archive/.stage.XXXXXXXX")
trap 'rm -rf -- "$scratch"' EXIT

# Keep a consistent published inode even if the next pull replaces cars.db.
(
    exec 8</srv/che168/pull.lock
    flock -s 8
    python3 - "$snapshot" <<'PY'
import sqlite3
import sys

with sqlite3.connect("file:" + sys.argv[1] + "?mode=ro", uri=True) as source:
    if source.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
        raise SystemExit("Повреждена опубликованная копия SQLite")
    if not source.execute("SELECT EXISTS(SELECT 1 FROM cars)").fetchone()[0]:
        raise SystemExit("Пустая копия SQLite")
PY
    zstd -q -3 -T1 -c "$snapshot" > "$scratch/sqlite.zst"
)
zstd -qt "$scratch/sqlite.zst"

sudo -u postgres pg_dump --dbname=avtopodborimport --format=custom --compress=4 > "$scratch/catalog.dump"
pg_restore --list "$scratch/catalog.dump" > "$scratch/contents"
for table in seller_description_translations brands brand_aliases model_aliases city_translations; do
    grep -Fq "TABLE DATA public $table " "$scratch/contents" || { echo "В архиве отсутствует $table"; exit 1; }
done
digest=$(sha256sum "$scratch/catalog.dump" | cut -d' ' -f1)

# Remote path is private and outside the document root. Verify before publishing or expiring anything.
ssh -o BatchMode=yes -o ConnectTimeout=20 hosting "set -eu
umask 077
dir=\$HOME/avto-private-backups/postgres
mkdir -p \"\$dir\"
chmod 700 \"\$HOME/avto-private-backups\" \"\$dir\"
cd \"\$dir\"
tmp=\$(mktemp .upload.XXXXXXXX)
trap 'rm -f -- \"\$tmp\"' EXIT
cat > \"\$tmp\"
printf '%s  %s\\n' '$digest' \"\$tmp\" | sha256sum -c - >/dev/null
mv -- \"\$tmp\" '$day.dump'
python3 -c 'from pathlib import Path; files=sorted(Path.cwd().glob(\"[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].dump\")); [p.unlink() for p in files[:-7]]'
" < "$scratch/catalog.dump"

mv -- "$scratch/sqlite.zst" "$archive/$day.sqlite.zst"
python3 - "$archive" <<'PY'
from pathlib import Path
import sys

files = sorted(Path(sys.argv[1]).glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].sqlite.zst"))
for old in files[:-7]:
    old.unlink()
PY
printf '%s PostgreSQL на хостинге сборщика: %s байт, SHA256 %s; SQLite на сервере сайта: %s байт\n' \
    "$day" "$(stat -c %s "$scratch/catalog.dump")" "$digest" "$(stat -c %s "$archive/$day.sqlite.zst")"
