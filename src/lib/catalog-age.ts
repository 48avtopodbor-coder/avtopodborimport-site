export const CATALOG_AGE_SQL =
  "(c.reg_month > (current_date + 45 - interval '5 years') AND (c.reg_month + interval '1 month' - interval '1 day') <= (current_date + 45 - interval '3 years'))";

export const CATALOG_VISIBLE_SQL = `c.is_active = 1 AND c.price_cny > 0 AND ${CATALOG_AGE_SQL}`;
