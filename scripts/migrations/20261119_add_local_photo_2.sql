-- Local path for the second Che168 photo. The importer deliberately leaves
-- both local photo columns untouched when it refreshes listing data.
ALTER TABLE cars
    ADD COLUMN IF NOT EXISTS local_photo_2 text;
