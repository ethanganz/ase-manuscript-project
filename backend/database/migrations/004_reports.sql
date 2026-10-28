-- FEATURE 04: REPORTS
-- Goal: A logged-in user can report someone else's collection. The owner sees
-- the report as a notification on their profile, without learning who sent it.
--
-- Safe to run again: on a database that already has the reports table,
-- only the missing columns, constraints and indexes are added.


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


-- STEP 2: WHO REPORTED, AND WHY
-- Added with "alter table" so they also reach a reports table that was
-- created before these columns existed.

alter table public.reports
  add column if not exists reporter_id uuid references public.users(id) on delete cascade;
  -- The user who sent the report. Never shown to the collection owner.

alter table public.reports
  add column if not exists reason text not null default 'other';
  -- One of the fixed reasons below.

alter table public.reports
  add column if not exists details text;
  -- Optional free text from the reporter.

alter table public.reports
  add column if not exists read_at timestamptz;
  -- When the owner marked the notification as read. Null = unread.

alter table public.reports
  drop constraint if exists reports_reason_check;
alter table public.reports
  add constraint reports_reason_check
  check (reason in ('spam', 'inappropriate', 'copyright', 'misleading', 'other'));

alter table public.reports
  drop constraint if exists reports_details_length;
alter table public.reports
  add constraint reports_details_length check (char_length(details) <= 1000);


-- STEP 3: MAKE SEARCHING FASTER
-- Helps the database find all reports of a collection quickly.

create index if not exists reports_collection_idx
  on public.reports (collection_id);

-- One report per user and collection, so one person cannot flood an owner
-- with notifications.
create unique index if not exists reports_collection_reporter_uniq
  on public.reports (collection_id, reporter_id);


-- STEP 4: PROTECT THE TABLE
-- Only the backend (service_role key) may access reports.

alter table public.reports enable row level security;
revoke all on public.reports from anon, authenticated;
