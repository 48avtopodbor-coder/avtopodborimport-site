#!/usr/bin/env python3
"""Export the current unknown terms/descriptions as one JSON document over SSH."""

import json
import os
import psycopg2
from catalog_age import NOT_AGED_OUT_SQL

with psycopg2.connect(
    os.environ.get("IMPORT_PG_DSN", "dbname=avtopodborimport user=postgres")
) as con:
    with con.cursor() as cur:
        cur.execute(
            "SELECT kind,scope,source_text,cars_count FROM catalog_translation_queue WHERE status='pending' AND cars_count>0 ORDER BY cars_count DESC"
        )
        terms = [dict(zip(("kind", "brand", "source", "cars"), r)) for r in cur]
        cur.execute(
            f"""SELECT t.source_text,count(*) FROM cars c
                JOIN seller_description_translations t
                  ON t.source_hash=md5(c.description) AND t.source_text=c.description
                WHERE c.is_active=1 AND c.price_cny>0 AND t.status='untranslated' AND {NOT_AGED_OUT_SQL}
                GROUP BY t.source_text ORDER BY count(*) DESC"""
        )
        descriptions = [{"text": text, "cars": n} for text, n in cur]
        print(
            json.dumps(
                {"terms": terms, "descriptions": descriptions}, ensure_ascii=False
            )
        )
