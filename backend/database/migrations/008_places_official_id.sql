-- FEATURE 08: PLACES FOUND BY THE HANDWRITING RECOGNITION
-- Goal: When a page has been transcribed, the places in its text appear on the
-- country map. The map reads public.places and public.place_mentions, so the
-- backend now fills them.
--
-- Safe to run again.


-- STEP 1: REMEMBER WHICH OFFICIAL PLACE A ROW COMES FROM
-- The official Bullinger place list has its own ids (for example "l587" =
-- Zürich). Keeping it next to our own uuid means the same place is stored once,
-- however many pages mention it, and a page can be transcribed again without
-- creating duplicates.

alter table public.places
  add column if not exists official_place_id text;

-- A plain unique index (not a partial one), because the backend upserts on it.
-- Rows without an official id (like the demo data) can still repeat: in a
-- unique index, empty (null) values never count as equal.
create unique index if not exists places_official_place_id_key
  on public.places (official_place_id);
