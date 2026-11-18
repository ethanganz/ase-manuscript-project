-- One row per transcribed line of handwriting.
create table if not exists public.text_lines (
  id                 uuid primary key default gen_random_uuid(),
  -- The uploaded page this line was read from. Empty until the line is linked
  -- to a page. Deleting the page deletes its lines.
  page_id            uuid references public.pages(id) on delete cascade,
  -- Identifiers assigned by the transcription system. source_line_id is the
  -- natural key: importing the same line twice updates it.
  source_document_id text,
  source_page_id     text,
  source_line_id     text not null unique,
  language           text,                 -- ISO 639-1 code, for example 'de' or 'la'
  text               text not null,        -- the transcribed line
  -- Search column kept up to date by Postgres. The 'simple' configuration does
  -- not cut word endings, which suits mixed German and Latin text.
  search             tsvector generated always as (to_tsvector('simple', text)) stored,
  created_at         timestamptz not null default now()
);

create index if not exists text_lines_search_idx on public.text_lines using gin (search);
create index if not exists text_lines_page_idx on public.text_lines (page_id);

-- Only the backend (service_role key) may read or write this table.
alter table public.text_lines enable row level security;

-- Just to test
-- insert into public.text_lines (source_line_id, language, text)
-- values ('test_1', 'la', 'Rex quidam Aphricanię exul factus vel');

-- select text from public.text_lines where search @@ plainto_tsquery('simple', 'exul');

-- delete from public.text_lines where source_line_id = 'test_1';