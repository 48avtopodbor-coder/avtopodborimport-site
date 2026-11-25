-- Restore Che168's grouped colours, using the preserved original, not guesses.
-- Run on the site after updating the collector and backfilling its saved details.
-- Safe to repeat; updates only the colour field and leaves the original JSON intact.
BEGIN;
WITH labels(source, translated) AS (
    VALUES ('银/灰色', 'серебристый / серый'),
           ('红/紫色', 'красный / фиолетовый'),
           ('香槟/棕色', 'шампань / коричневый'),
           ('黄/橙色', 'жёлтый / оранжевый')
)
UPDATE cars AS c
SET color = labels.translated
FROM labels
WHERE CASE WHEN pg_input_is_valid(c.details_json, 'json')
           THEN c.details_json::json->>'colorname' END = labels.source
  AND c.color IS DISTINCT FROM labels.translated;
COMMIT;
