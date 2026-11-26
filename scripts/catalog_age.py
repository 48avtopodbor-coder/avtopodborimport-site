"""PostgreSQL age predicates for catalog background jobs (cars alias c)."""

# Keep the full-window predicate in sync with src/lib/catalog-age.ts.
OLDEST_REGISTRATION_SQL = "c.reg_month > (current_date + 45 - interval '5 years')"
CUSTOMS_AGE_SQL = (
    f"({OLDEST_REGISTRATION_SQL} AND "
    "(c.reg_month + interval '1 month' - interval '1 day') <= "
    "(current_date + 45 - interval '3 years'))"
)
# Unknown months stay in the background queues until they can be classified.
NOT_AGED_OUT_SQL = f"({OLDEST_REGISTRATION_SQL} OR c.reg_month IS NULL)"
