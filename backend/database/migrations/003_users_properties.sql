-- Migration: Replace display_name with first_name and last_name

-- STEP 1: Rename display_name to first_name
alter table public.users
  rename column display_name to first_name;

-- STEP 2: Add last_name
alter table public.users
  add column last_name text;