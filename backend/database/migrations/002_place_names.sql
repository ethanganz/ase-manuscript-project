-- FEATURE 02: PLACES ON THE MAP
-- Goal: Store places found in our documents and connect them
-- to the pages where they appear.


-- STEP 1: CREATE THE PLACES TABLE
-- This table stores each place, such as Geneva or Paris.
-- Each place has a name, country, and optional map coordinates.

create table if not exists public.places (
  id           uuid primary key default gen_random_uuid(),
  -- Creates a unique ID for each place automatically.

  name         text not null,
  -- Stores the place name. It cannot be empty.

  country_code char(2),
  -- Stores the 2-letter country code, such as CH or FR.

  lat          double precision,
  -- Stores latitude: the north/south position on the map.

  lng          double precision,
  -- Stores longitude: the east/west position on the map.

  created_at   timestamptz not null default now(),
  -- Automatically saves when the place was added.

  constraint places_country_code_upper
  check (country_code is null or country_code = upper(country_code))
  -- Ensures the country code uses uppercase letters.
  -- Example: CH is accepted; ch is rejected.
);


-- STEP 2: CREATE THE PLACE_MENTIONS TABLE
-- This table records every time a place appears on a document page.
-- It connects a place to the page where it was found.
-- Example: Geneva appears on page 5 of a manuscript.

create table if not exists public.place_mentions (
  id         uuid primary key default gen_random_uuid(),
  -- Creates a unique ID for each occurrence of a place.

  place_id   uuid not null references public.places(id) on delete cascade,
  -- Connects this mention to a place in the places table.
  -- If that place is deleted, its mentions are deleted too.

  page_id    uuid not null references public.pages(id) on delete cascade,
  -- Connects the mention to a page in the pages table.
  -- If that page is deleted, its mentions are deleted too.

  snippet    text,
  -- Stores a short excerpt of text around the place name.
  -- This can be displayed when someone clicks the place.

  created_at timestamptz not null default now()
  -- Saves when this mention was recorded.
);


-- STEP 3: MAKE SEARCHING FASTER
-- These indexes help the database find mentions by page or by place
-- more quickly, especially when there is lots of data.

create index if not exists place_mentions_page_idx
  on public.place_mentions (page_id);

create index if not exists place_mentions_place_idx
  on public.place_mentions (place_id);


-- STEP 4: PROTECT THE TABLES
-- Enables Row-Level Security (RLS) on both tables.
-- This lets database security policies control who can access the data.
-- The comment below describes the intended protection:
-- only the backend service_role should use these tables.
-- IMPORTANT: Enabling RLS alone does not grant access exclusively
-- to service_role; permissions and security policies also matter.

alter table public.places enable row level security;
alter table public.place_mentions enable row level security;


-- STEP 5: CREATE A VIEW WITH ALL THE MAP INFORMATION
-- A view combines information from several tables into one result.
-- It connects each place mention to its place, page, and document.
-- This makes it easier for the backend to get everything the map needs.

create or replace view public.mention_details
with (security_invoker = true) as

select
  m.id as mention_id,
  -- ID of this particular mention.

  m.snippet,
  -- Text excerpt showing the context around the place.

  p.name as place_name,
  -- Name of the place, such as Geneva.

  p.country_code::text as country_code,
  -- Country code, such as CH or FR, returned as text.

  p.lat,
  p.lng,
  -- Coordinates used to position the place on the map.

  pg.id as page_id,
  pg.page_number,
  -- Identifies the page and its page number.

  d.id as document_id,
  d.original_filename as document_name,
  d.collection_id
  -- Identifies the original document and its collection.

from public.place_mentions m

join public.places p
  on p.id = m.place_id
-- Finds the place associated with each mention.

join public.pages pg
  on pg.id = m.page_id
-- Finds the page where the place was mentioned.

join public.documents d
  on d.id = pg.document_id;
-- Finds the document containing that page.


-- STEP 6: BLOCK PUBLIC-KEY USERS FROM READING THE VIEW
-- Removes all privileges on this view from the anon and authenticated
-- database roles. These are commonly used for unauthenticated and
-- signed-in client access in Supabase.
-- The backend can access it only if its role has the required privileges.

revoke all on public.mention_details from anon, authenticated;
