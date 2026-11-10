-- Typo-tolerant, accent-blind search over transcribed lines.
--
-- * pg_trgm compares words by their three-letter pieces ("trigrams"), so a word
--   with one wrong letter, which handwriting recognition often produces, still matches.
-- * unaccent removes accents, so "Zurich" finds "Zürich" and "Basilea" finds "Basileę".

create extension if not exists pg_trgm with schema extensions;
create extension if not exists unaccent with schema extensions;

-- Generated columns and indexes need an IMMUTABLE function. unaccent itself is
-- only marked STABLE, so we wrap it with a fixed dictionary, which never changes.
create or replace function public.fold_text(input text)
returns text
language sql
immutable
parallel safe
strict
as $$ select lower(extensions.unaccent('extensions.unaccent'::regdictionary, input)) $$;

-- The line in lower case without accents. Postgres keeps it up to date.
alter table public.text_lines
  add column if not exists text_folded text generated always as (public.fold_text(text)) stored;

create index if not exists text_lines_folded_trgm_idx
  on public.text_lines using gin (text_folded extensions.gin_trgm_ops);

create or replace function public.search_text_lines(
  query_words text[],
  collection  uuid default null,
  max_results int  default 20
)
returns table (
  id uuid, page_id uuid, source_line_id text, language text, text text, score real
)
language sql
stable
set search_path = public, extensions
as $$
  with words as (
    select distinct public.fold_text(w) as w
      from unnest(query_words) as w
     where length(trim(w)) > 0
  )
  select t.id, t.page_id, t.source_line_id, t.language, t.text,
         -- A line scores the sum of its matching words' similarity (0 to 1 each),
         -- so a line that matches two query words beats a line that matches one.
         (select sum(word_similarity(words.w, t.text_folded))
            from words
           where words.w <% t.text_folded)::real as score
  from public.text_lines t
  where exists (select 1 from words where words.w <% t.text_folded)
    and (collection is null
         or t.page_id in (select p.id
                            from public.pages p
                            join public.documents d on d.id = p.document_id
                           where d.collection_id = collection))
  order by score desc, t.source_line_id
  limit greatest(1, least(max_results, 100));
$$;

-- Only the backend (service_role key) may call it.
revoke all on function public.search_text_lines(text[], uuid, int) from public, anon, authenticated;
grant execute on function public.search_text_lines(text[], uuid, int) to service_role;