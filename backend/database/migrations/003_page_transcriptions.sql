alter table public.pages
  add column if not exists transcription_text text;
