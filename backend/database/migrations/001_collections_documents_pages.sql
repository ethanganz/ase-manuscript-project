create extension if not exists pgcrypto;

create table if not exists public.collections (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  description text,
  created_at  timestamptz not null default now()
);

create table if not exists public.documents (
  id                uuid primary key,
  collection_id     uuid not null references public.collections(id) on delete cascade,
  original_filename text not null,
  source_archive    text,
  file_type         text not null check (file_type in ('pdf', 'jpeg', 'png', 'heic')),
  size_bytes        bigint not null,
  sha256            text not null,
  status            text not null default 'uploaded',
  original_path     text not null,
  created_at        timestamptz not null default now()
);
create index if not exists documents_collection_idx on public.documents (collection_id);
create index if not exists documents_sha256_idx on public.documents (sha256);

create table if not exists public.pages (
  id            uuid primary key,
  document_id   uuid not null references public.documents(id) on delete cascade,
  collection_id uuid not null references public.collections(id) on delete cascade,
  page_number   integer not null,
  image_path    text not null,
  width         integer not null,
  height        integer not null,
  status        text not null default 'pending',
  created_at    timestamptz not null default now(),
  unique (document_id, page_number)
);
create index if not exists pages_document_idx on public.pages (document_id);

alter table public.collections enable row level security;
alter table public.documents   enable row level security;
alter table public.pages       enable row level security;