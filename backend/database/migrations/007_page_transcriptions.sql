-- FEATURE 07: LINE-BY-LINE TRANSCRIPTION
-- Goal: Store what the HTR-NLP pipeline reads from each page, one row per
-- handwritten line, and track how far the recognition of each page is.
--
-- Safe to run again.


-- STEP 1: TRACK THE RECOGNITION OF EACH PAGE
-- pages.status already exists. It now moves through:
--   pending  -> uploaded, nobody asked for recognition yet
--   queued   -> waiting for the recognition worker
--   running  -> the worker is reading the page right now
--   complete -> the lines are stored in page_lines
--   failed   -> something went wrong; htr_error says what

alter table public.pages
  add column if not exists htr_error       text;
alter table public.pages
  add column if not exists htr_width       integer;
alter table public.pages
  add column if not exists htr_height      integer;
  -- Size of the page image the line boxes refer to (after rotating it upright).
alter table public.pages
  add column if not exists htr_finished_at timestamptz;


-- STEP 2: ONE ROW PER LINE OF TEXT

create table if not exists public.page_lines (
  id         uuid primary key default gen_random_uuid(),

  page_id    uuid not null references public.pages(id) on delete cascade,
  -- If the page is deleted, its lines are deleted too.

  line_index integer not null,
  -- 0 = top line. Lines are shown in this order.

  text       text not null default '',
  -- The text the model read from this line. Empty if it read nothing.

  bbox       jsonb,
  -- [left, top, right, bottom] in pixels of the upright page image.

  polygon    jsonb,
  -- Outline of the line, [[x, y], ...], same pixel frame as bbox.

  places     jsonb not null default '[]'::jsonb,
  -- Place mentions found in this line: start, end (Unicode code points,
  -- end exclusive), text, place_link_status and the FULL list of
  -- official_place_candidates. Kept exactly as the pipeline returned it.

  created_at timestamptz not null default now(),

  unique (page_id, line_index)
);

create index if not exists page_lines_page_idx on public.page_lines (page_id);


-- STEP 3: PROTECT THE TABLE
-- Only the backend (service_role key) reads and writes this table.

alter table public.page_lines enable row level security;
