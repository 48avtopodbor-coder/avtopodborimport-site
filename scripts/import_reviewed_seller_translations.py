#!/usr/bin/env python3
"""Import independently checked seller translations into PostgreSQL.

Only complete Russian translations marked qa_checked are imported. Existing
dictionary translations keep priority. Source text must exactly match a car.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re


DSN = os.environ.get("IMPORT_PG_DSN", "postgresql://postgres@/avtopodborimport?host=/var/run/postgresql")
CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
RUSSIAN = re.compile(r"[А-Яа-яЁё]")
LATIN = re.compile(r"[A-Za-z]")


def read_complete_jsonl(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.endswith("\n") and line.strip()]


def prepare(rows):
    ready = {}
    rejected = {"not_checked": 0, "chinese_remaining": 0, "missing_russian": 0}
    for row in rows:
        source = row.get("text", "")
        translated = row.get("ru", "").strip()
        if not row.get("qa_checked") or not source:
            rejected["not_checked"] += 1
            continue
        if CJK.search(translated) or row.get("qa_unresolved_cjk"):
            rejected["chinese_remaining"] += 1
            continue
        brand_only = len(source) < 30 and LATIN.search(translated)
        if (not RUSSIAN.search(translated) and not brand_only) or len(translated) < 5:
            rejected["missing_russian"] += 1
            continue
        source_hash = hashlib.md5(source.encode("utf-8")).hexdigest()
        ready[source_hash] = (source_hash, source, translated)
    return list(ready.values()), rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviewed", type=Path)
    parser.add_argument("--apply", action="store_true", help="Записать в базу; без флага только проверить файл")
    args = parser.parse_args()
    rows, rejected = prepare(read_complete_jsonl(args.reviewed))
    print(json.dumps({"ready": len(rows), "rejected": rejected}, ensure_ascii=False), flush=True)
    if not args.apply or not rows:
        return
    import psycopg2
    from psycopg2.extras import execute_batch

    with psycopg2.connect(DSN) as connection:
        with connection.cursor() as cursor:
            execute_batch(cursor, """
                INSERT INTO seller_description_translations
                    (source_hash, source_text, status, translated_text, dictionary_revision)
                VALUES (%s, %s, 'reviewed', %s, NULL)
                ON CONFLICT (source_hash) DO UPDATE
                SET status = 'reviewed', translated_text = EXCLUDED.translated_text,
                    dictionary_revision = NULL, updated_at = now()
                WHERE seller_description_translations.source_text = EXCLUDED.source_text
                  AND (seller_description_translations.status <> 'dictionary'
                       OR seller_description_translations.translated_text ~ '[一-龥]')
                  AND (seller_description_translations.status <> 'reviewed'
                       OR seller_description_translations.translated_text IS DISTINCT FROM EXCLUDED.translated_text)
            """, rows, page_size=200)
    print(f"В базу отправлено {len(rows)} проверенных переводов", flush=True)


if __name__ == "__main__":
    main()
