#!/bin/sh
# Использует словарь из работающей версии сайта и ограничивает нагрузку на сервер.
set -eu

temporary=$(mktemp /opt/avtopodborimport/seller-dictionary.XXXXXXXX)
cleanup() {
  rm -f "$temporary"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

docker cp avtopodbor-web:/app/seller-dictionary.json "$temporary"
python3 - "$temporary" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    data = json.load(source)
if not isinstance(data.get("descriptions"), dict) or not isinstance(data.get("phrases"), dict):
    raise SystemExit("неверный формат словаря")
PY
chmod 644 "$temporary"
mv -f "$temporary" /opt/avtopodborimport/seller-dictionary.json

exec nice -n 15 sudo -u postgres python3 \
  /opt/avtopodborimport/translate_seller_descriptions.py --limit 2000
