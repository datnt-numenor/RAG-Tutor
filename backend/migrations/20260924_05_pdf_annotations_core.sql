-- PDF annotation core. Coordinates are stored normalized to [0,1].

create table if not exists public.notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  project_id uuid not null references public.projects(id) on delete cascade,
  document_id uuid not null references public.documents(id) on delete cascade,
  document_version_id uuid not null references public.document_versions(id) on delete cascade,
  page_number integer not null check (page_number > 0),
  annotation_type text not null check (annotation_type in ('text_highlight','rectangle')),
  selected_text text,
  rectangles jsonb,
  content text,
  color text not null default '#F4D06F',
  version integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists notes_user_version_page_idx
  on public.notes(user_id, document_version_id, page_number);

create index if not exists notes_document_id_idx
  on public.notes(document_id);

alter table public.notes enable row level security;
