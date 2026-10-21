-- FEATURE 04: REPORTS
-- Goal: Store reports that belong to a collection.


-- STEP 1: CREATE THE REPORTS TABLE

create table if not exists public.reports (
  id            uuid primary key default gen_random_uuid(),
  -- Creates a unique ID for each report automatically.

  collection_id uuid not null references public.collections(id) on delete cascade,
  -- Connects the report to a collection.
  -- If that collection is deleted, its reports are deleted too.

  created_at    timestamptz not null default now()
  -- Automatically saves when the report was created.
);


-- STEP 2: MAKE SEARCHING FASTER
-- Helps the database find all reports of a collection quickly.

create index if not exists reports_collection_idx
  on public.reports (collection_id);


-- STEP 3: PROTECT THE TABLE
-- Only the backend (service_role key) may access reports.

alter table public.reports enable row level security;
revoke all on public.reports from anon, authenticated;
