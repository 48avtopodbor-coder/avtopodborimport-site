BEGIN;
CREATE TABLE IF NOT EXISTS catalog_translation_queue (
 kind text NOT NULL CHECK (kind IN ('brand','model','city')),
 scope text NOT NULL DEFAULT '', source_text text NOT NULL,
 cars_count integer NOT NULL DEFAULT 0,
 status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','applied')),
 first_seen timestamptz NOT NULL DEFAULT now(), last_seen timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(kind,scope,source_text)
);
CREATE OR REPLACE VIEW catalog_translation_health AS
SELECT 'model' AS kind, count(*) AS missing FROM cars WHERE is_active=1 AND price_cny>0 AND model_name IS NULL
UNION ALL SELECT 'brand',count(*) FROM cars WHERE is_active=1 AND price_cny>0 AND brand_id IS NULL
UNION ALL SELECT 'city',count(*) FROM cars c LEFT JOIN city_translations t ON t.city_cn=c.city WHERE c.is_active=1 AND c.price_cny>0 AND t.city_cn IS NULL
UNION ALL SELECT 'description',count(*) FROM cars c LEFT JOIN seller_description_translations t ON t.source_hash=md5(c.description) AND t.source_text=c.description WHERE c.is_active=1 AND c.price_cny>0 AND nullif(trim(c.description),'') IS NOT NULL AND (t.status IN ('untranslated','pending') OR t.source_hash IS NULL);
COMMIT;
ALTER TABLE city_translations ADD COLUMN IF NOT EXISTS distance_source text;
