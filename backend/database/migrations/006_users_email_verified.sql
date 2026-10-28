-- FEATURE 06: EMAIL VERIFICATION
-- Goal: A new account must confirm its email address before it can log in.
-- The backend emails a link (sent with Resend); opening it verifies the account.


-- STEP 1: ADD THE VERIFICATION COLUMNS

alter table public.users
  add column if not exists email_verified boolean not null default false;
  -- false = the user has not opened the link yet and cannot log in.

alter table public.users
  add column if not exists email_verified_at timestamptz;
  -- When the link was opened. Null while unverified.


-- STEP 2: KEEP EXISTING ACCOUNTS WORKING
-- Accounts created before this migration never got an email, so they are
-- treated as verified. Otherwise their owners would be locked out.

update public.users
  set email_verified = true,
      email_verified_at = coalesce(email_verified_at, now())
  where email_verified = false;
