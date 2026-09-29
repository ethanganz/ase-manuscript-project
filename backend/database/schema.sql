-- Schema for the name-submission app.
-- Run this in the Supabase SQL editor (Dashboard -> SQL Editor).
--
-- The table has a single column, `name`, as required.

create table if not exists public.names (
  name text not null
);

-- Row Level Security: enabled so access is explicit. The policy below allows
-- full access for the `anon` / `authenticated` roles so the app works whether
-- it connects with the `anon` key (subject to RLS) or the `service_role` key
-- (bypasses RLS).
alter table public.names enable row level security;

drop policy if exists "allow all on names" on public.names;
create policy "allow all on names" on public.names
  to anon, authenticated
  for all
  using (true)
  with check (true);