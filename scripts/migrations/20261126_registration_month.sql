BEGIN;

ALTER TABLE cars ADD COLUMN IF NOT EXISTS reg_month date;

-- Keep this compatible with scripts/collector/registration_age.py.
CREATE OR REPLACE FUNCTION car_registration_month(first_reg_date text, fallback_year integer)
RETURNS date LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE AS $$
DECLARE
    value text := regexp_replace(coalesce(first_reg_date, ''), '^[[:space:]]+|[[:space:]]+$', '', 'g');
    parts text[];
    y text;
    m text;
    d text;
BEGIN
    parts := regexp_match(value, '^([0-9]{4})([-/.])([0-9]{1,2})(?:\2([0-9]{1,2}))?$');
    IF parts IS NOT NULL THEN
        y := parts[1]; m := parts[3]; d := parts[4];
    ELSE
        parts := regexp_match(value, '^([0-9]{4})年([0-9]{1,2})月(?:([0-9]{1,2})日)?$');
        IF parts IS NOT NULL THEN
            y := parts[1]; m := parts[2]; d := parts[3];
        ELSE
            parts := regexp_match(value, '^([0-9]{1,2})\.([0-9]{1,2})\.([0-9]{4})$');
            IF parts IS NOT NULL THEN
                y := parts[3]; m := parts[2]; d := parts[1];
            END IF;
        END IF;
    END IF;

    IF y IS NOT NULL AND pg_input_is_valid(y || '-' || lpad(m, 2, '0') || '-' || lpad(coalesce(d, '1'), 2, '0'), 'date') THEN
        RETURN make_date(y::int, m::int, 1);
    END IF;
    IF fallback_year BETWEEN 1 AND 9999 THEN
        RETURN make_date(fallback_year, 7, 1);
    END IF;
    RETURN NULL;
END;
$$;

UPDATE cars
SET reg_month = car_registration_month(first_reg_date, year)
WHERE reg_month IS DISTINCT FROM car_registration_month(first_reg_date, year);

CREATE INDEX IF NOT EXISTS idx_cars_catalog_reg_month ON cars (reg_month)
    WHERE is_active = 1 AND price_cny > 0;

COMMIT;
