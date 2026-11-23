CREATE TABLE IF NOT EXISTS sold_car_cleanup (
    listing_id text PRIMARY KEY,
    cache_keys jsonb NOT NULL DEFAULT '[]'::jsonb,
    queued_at timestamptz NOT NULL DEFAULT now(),
    cleaned_at timestamptz
);
