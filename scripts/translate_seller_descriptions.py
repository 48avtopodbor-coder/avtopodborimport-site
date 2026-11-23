#!/usr/bin/env python3
"""Заполнение очереди описаний и перевод известных полных текстов по словарю."""
import argparse
import hashlib
import json
import os
import re
import sys

DSN = os.environ.get("IMPORT_PG_DSN", "postgresql://postgres@/avtopodborimport?host=/var/run/postgresql")
DICTIONARY = os.environ.get("SELLER_DICTIONARY", "/opt/avtopodborimport/seller-dictionary.json")
CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")


def load_dictionary(path):
    with open(path, encoding="utf-8") as source:
        data = json.load(source)
    canonical = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    revision = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return data, revision


def translate(original, dictionary):
    text = original.strip()
    normalized = re.sub(r"\s+", "", re.sub(r"[。．.]+$", "", re.sub(r"[，,]", "，", text)))
    result = dictionary["descriptions"].get(normalized)
    if result:
        return ("untranslated", None) if CJK.search(result) else ("dictionary", result)
    if CJK.search(text):
        parts = [part for part in re.split(r"[，。；;、]+", normalized) if part]
        phrases = dictionary["phrases"]
        if parts and all(part in phrases for part in parts):
            result = " ".join(f"{phrases[part]}." for part in parts)
            return ("untranslated", None) if CJK.search(result) else ("dictionary", result)
        return "untranslated", None
    return "original", None


def main():
    import psycopg2
    from psycopg2.extras import execute_batch

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit должен быть положительным")
    dictionary, revision = load_dictionary(DICTIONARY)
    connection = psycopg2.connect(DSN)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(hashtext('avtopodbor_seller_translations'))")
            if not cursor.fetchone()[0]:
                print("обработка переводов уже выполняется")
                return
        connection.commit()
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO seller_description_translations (source_hash, source_text)
                    SELECT md5(description), description FROM cars
                    WHERE is_active = 1 AND price_cny > 0 AND NULLIF(trim(description), '') IS NOT NULL
                    GROUP BY description
                    ON CONFLICT (source_hash) DO NOTHING
                """)
                added = cursor.rowcount
        processed = 0
        while processed < args.limit:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT source_hash, source_text FROM seller_description_translations
                        WHERE status <> 'reviewed'
                          AND dictionary_revision IS DISTINCT FROM %s
                        ORDER BY CASE status WHEN 'dictionary' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END,
                                 updated_at, source_hash
                        LIMIT %s FOR UPDATE SKIP LOCKED
                    """, (revision, min(200, args.limit - processed)))
                    rows = cursor.fetchall()
                    if not rows:
                        break
                    updates = []
                    for source_hash, source_text in rows:
                        status, translated = translate(source_text, dictionary)
                        updates.append((status, translated, revision, source_hash, source_text))
                    execute_batch(cursor, """
                        UPDATE seller_description_translations
                        SET status = %s, translated_text = %s, dictionary_revision = %s,
                            updated_at = now()
                        WHERE source_hash = %s AND source_text = %s
                    """, updates)
                    processed += len(rows)
        print(f"в очередь добавлено: {added}; обработано: {processed}; версия словаря: {revision[:12]}")
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ошибка обработки переводов: {type(error).__name__}: {error}", file=sys.stderr)
        raise
