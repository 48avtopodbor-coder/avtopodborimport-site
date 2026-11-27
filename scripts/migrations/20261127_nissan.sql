BEGIN;

INSERT INTO brands (slug, name, name_cn, logo_path)
VALUES ('nissan', 'Nissan', '日产', '/brands/nissan.svg')
ON CONFLICT (slug) DO UPDATE SET name_cn = EXCLUDED.name_cn, logo_path = EXCLUDED.logo_path;

INSERT INTO brand_aliases (brand_id, alias_norm)
SELECT b.id, a.alias FROM brands b CROSS JOIN (VALUES ('nissan'), ('日产')) a(alias)
WHERE b.slug = 'nissan' ON CONFLICT (alias_norm) DO NOTHING;

-- Exact Che168 series labels. Several series include both scripts.
INSERT INTO model_aliases (brand_id, source_series, model_name, model_slug, source_url)
SELECT b.id, a.series, a.name, a.slug, a.source FROM brands b CROSS JOIN (VALUES
  ('奇骏', 'X-Trail', 'x-trail', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html'),
  ('逍客', 'Qashqai', 'qashqai', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html'),
  ('轩逸', 'Sylphy', 'sylphy', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html'),
  ('天籁', 'Teana', 'teana', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html'),
  ('楼兰', 'Murano', 'murano', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html'),
  ('劲客', 'Kicks', 'kicks', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html'),
  ('骐达', 'Tiida', 'tiida', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html'),
  ('骐达TIIDA', 'Tiida', 'tiida', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html'),
  ('探陆', 'Pathfinder', 'pathfinder', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html'),
  ('途乐', 'Patrol', 'patrol', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html'),
  ('艾睿雅', 'Ariya', 'ariya', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html'),
  ('ARIYA艾睿雅', 'Ariya', 'ariya', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html'),
  ('纳瓦拉', 'Navara', 'navara', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html'),
  ('途达', 'Terra', 'terra', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html'),
  ('日产GT-R', 'GT-R', 'gt-r', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html'),
  ('蓝鸟', 'Lannia', 'lannia', 'https://www.autohome.com.cn/cars/brand-63-x-x-x-x-1.html')
) a(series, name, slug, source)
WHERE b.slug = 'nissan'
ON CONFLICT (brand_id, source_series) DO UPDATE SET
  model_name = EXCLUDED.model_name, model_slug = EXCLUDED.model_slug, source_url = EXCLUDED.source_url;

COMMIT;
