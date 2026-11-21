-- Кэш и очередь: одинаковый исходный текст хранится и переводится один раз.
CREATE TABLE IF NOT EXISTS seller_description_translations (
    source_hash text PRIMARY KEY,
    source_text text NOT NULL,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'dictionary', 'untranslated', 'original')),
    translated_text text,
    dictionary_revision text,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (source_hash = md5(source_text)),
    CHECK ((status = 'dictionary' AND translated_text IS NOT NULL)
        OR (status <> 'dictionary' AND translated_text IS NULL))
);
CREATE INDEX IF NOT EXISTS seller_description_translations_work_idx
    ON seller_description_translations (dictionary_revision, status);
GRANT SELECT ON seller_description_translations TO avtosite;

-- Отчёт для администратора: повторяющиеся фрагменты ещё не переведённых описаний.
CREATE OR REPLACE VIEW seller_untranslated_fragments AS
SELECT btrim(fragment) AS phrase, count(*) AS occurrences
FROM cars c
JOIN seller_description_translations t
  ON t.source_hash = md5(c.description) AND t.source_text = c.description
CROSS JOIN LATERAL regexp_split_to_table(c.description, '[，。；;、\n\r]+') AS fragment
WHERE c.is_active = 1 AND c.price_cny > 0 AND t.status = 'untranslated'
  AND btrim(fragment) <> ''
GROUP BY btrim(fragment);
