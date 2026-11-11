-- FEATURE 07: HANDWRITING RECOGNITION
-- Goal: Uploaded pages are sent to the HTR service (htr/service) and the
-- recognized lines are stored on the page.


-- STEP 1: THE LANGUAGE CHOSEN AT UPLOAD

alter table public.documents
  add column if not exists language text check (language in ('de', 'la'));
  -- German or Latin, used to rerank the recognized text. Null = unknown.


-- STEP 2: THE RESULT ON EACH PAGE
-- pages.status is now one of:
--   pending     not sent for recognition (HTR service not configured)
--   queued      waiting for the HTR service
--   processing  being recognized right now
--   done        transcription is filled in
--   failed      transcription_error says why

alter table public.pages
  add column if not exists transcription jsonb;
  -- {"lines": [{"text", "bbox": [left, top, right, bottom], "places": [...]}], ...}

alter table public.pages
  add column if not exists transcription_error text;

alter table public.pages
  add column if not exists transcribed_at timestamptz;
