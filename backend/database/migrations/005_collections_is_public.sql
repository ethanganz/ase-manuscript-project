-- FEATURE 05: PUBLIC AND PRIVATE COLLECTIONS
-- Goal: The owner chooses whether everyone can see a collection (public)
-- or only they can (private).


-- STEP 1: ADD THE IS_PUBLIC COLUMN
-- Existing collections become public, so nothing that is visible today
-- disappears after this migration.

alter table public.collections
  add column if not exists is_public boolean not null default true;
  -- true  = everyone can browse it.
  -- false = only the owner can see it. The backend enforces this.


-- STEP 2: MAKE SEARCHING FASTER
-- The collections list asks for "public ones, plus my own" on every visit.

create index if not exists collections_is_public_idx
  on public.collections (is_public);
