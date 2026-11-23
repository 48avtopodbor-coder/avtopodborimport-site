BEGIN;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS price_rub numeric;
CREATE TABLE IF NOT EXISTS catalog_spec_bodies (
 spec_id text PRIMARY KEY REFERENCES specs(spec_id) ON DELETE CASCADE,
 source_text text,
 body_slug text
);
CREATE OR REPLACE FUNCTION catalog_body_text(raw text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
 SELECT pair->>1 FROM jsonb_array_elements(CASE WHEN pg_input_is_valid(raw,'jsonb') THEN CASE WHEN jsonb_typeof(raw::jsonb)='array' THEN raw::jsonb ELSE '[]'::jsonb END ELSE '[]'::jsonb END) section
 CROSS JOIN LATERAL jsonb_array_elements(CASE WHEN jsonb_typeof(section->1)='array' THEN section->1 ELSE '[]'::jsonb END) pair
 WHERE pair->>0='车身结构'
 ORDER BY CASE WHEN section->>0='车身' THEN 0 ELSE 1 END LIMIT 1
$$;
CREATE OR REPLACE FUNCTION catalog_body_slug(raw text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
 SELECT CASE
 WHEN raw ~ '敞篷' THEN 'convertible'
 WHEN raw ~* 'SUV' THEN 'suv'
 WHEN raw ~* 'MPV' THEN 'mpv'
 WHEN raw ~ '皮卡' THEN 'pickup'
 WHEN raw ~ '旅行' THEN 'wagon'
 WHEN raw ~ '掀背|两厢' THEN 'hatchback'
 WHEN raw ~ '跑车|硬顶跑车' THEN 'coupe'
 WHEN raw ~ '三厢' THEN 'sedan'
 WHEN raw ~ '客车|货车' THEN 'van'
 ELSE NULL END
$$;
CREATE OR REPLACE FUNCTION refresh_catalog_body() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE body text;
BEGIN
 body := catalog_body_text(NEW.params_json);
 INSERT INTO catalog_spec_bodies(spec_id,source_text,body_slug) VALUES(NEW.spec_id,body,catalog_body_slug(body))
 ON CONFLICT(spec_id) DO UPDATE SET source_text=EXCLUDED.source_text,body_slug=EXCLUDED.body_slug;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS catalog_body_refresh ON specs;
CREATE TRIGGER catalog_body_refresh AFTER INSERT OR UPDATE OF params_json ON specs FOR EACH ROW EXECUTE FUNCTION refresh_catalog_body();
INSERT INTO catalog_spec_bodies(spec_id,source_text,body_slug)
 SELECT spec_id,catalog_body_text(params_json),catalog_body_slug(catalog_body_text(params_json)) FROM specs
 ON CONFLICT(spec_id) DO UPDATE SET source_text=EXCLUDED.source_text,body_slug=EXCLUDED.body_slug;
CREATE OR REPLACE FUNCTION register_catalog_brand() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE raw text; new_slug text; new_id integer;
BEGIN
 raw := COALESCE(NULLIF(btrim(NEW.brand_ru),''),NULLIF(btrim(NEW.brand_cn),''));
 IF raw IS NULL THEN RETURN NEW; END IF;
 new_slug := CASE WHEN raw ~ '^[A-Za-z][A-Za-z0-9 .&+-]{0,79}$'
 THEN trim(both '-' from regexp_replace(lower(raw),'[^a-z0-9]+','-','g'))
 ELSE 'brand-' || substr(md5(raw),1,12) END;
 INSERT INTO brands(slug,name,name_cn) VALUES(new_slug,raw,NEW.brand_cn) ON CONFLICT(slug) DO NOTHING RETURNING id INTO new_id;
 IF new_id IS NOT NULL THEN RAISE LOG 'Catalog brand registered without logo: % (%)',raw,new_slug; END IF;
 INSERT INTO unmapped_brand_names(raw_name) VALUES(raw) ON CONFLICT(raw_name) DO UPDATE SET last_seen=now();
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS catalog_register_brand ON cars;
CREATE TRIGGER catalog_register_brand AFTER INSERT OR UPDATE OF brand_ru,brand_cn ON cars FOR EACH ROW WHEN(NEW.brand_id IS NULL) EXECUTE FUNCTION register_catalog_brand();
CREATE INDEX IF NOT EXISTS catalog_body_slug_idx ON catalog_spec_bodies(body_slug,spec_id);
CREATE INDEX IF NOT EXISTS catalog_active_newest_idx ON cars(scraped_at DESC,listing_id DESC) WHERE is_active=1 AND price_cny>0;
CREATE INDEX IF NOT EXISTS catalog_active_rub_idx ON cars(price_rub) WHERE is_active=1 AND price_cny>0 AND price_rub IS NOT NULL;
COMMIT;
