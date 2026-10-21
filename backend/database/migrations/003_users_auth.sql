-- FEATURE 03: USER ACCOUNTS
-- Goal: Let people sign up and log in, and give every collection an owner.
-- Everyone can browse; only logged-in users can create collections, and only
-- the owner can upload into a collection.


-- STEP 1: CREATE THE USERS TABLE
-- Passwords are never stored, only a bcrypt hash made by the backend.

create table if not exists public.users (
  id            uuid primary key default gen_random_uuid(),
  -- Creates a unique ID for each user automatically.

  email         text not null unique,
  -- The login name. The backend stores it in lowercase.

  password_hash text not null,
  -- bcrypt hash of the password.

  display_name  text,
  -- Optional name shown in the app.

  created_at    timestamptz not null default now(),
  -- Saves when the account was created.

  constraint users_email_lower check (email = lower(email))
  -- Ensures "Anna@Mail.com" and "anna@mail.com" are the same account.
);


-- STEP 2: CONNECT COLLECTIONS TO THEIR OWNER
-- If a user is deleted, their collections (and, through the existing
-- cascades, their documents, pages and mentions) are deleted too.

alter table public.collections
  add column if not exists owner_id uuid references public.users(id) on delete cascade;

create index if not exists collections_owner_idx on public.collections (owner_id);

-- Collections created before this migration have no owner: everyone can
-- still see them, but nobody can upload into them. To give them to a user
-- after they have registered:
-- update public.collections
--   set owner_id = (select id from public.users where email = 'you@example.com')
--   where owner_id is null;


-- STEP 3: PROTECT THE TABLE
-- Only the backend (service_role key) may read password hashes.

alter table public.users enable row level security;
revoke all on public.users from anon, authenticated;
