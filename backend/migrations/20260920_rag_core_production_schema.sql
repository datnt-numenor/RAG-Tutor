-- RAGTutor production RAG core schema
-- Applied to Supabase on 2026-09-20.

create extension if not exists vector;
create extension if not exists pgcrypto;

create table if not exists public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null unique,
  full_name text,
  avatar_url text,
  timezone text not null default 'Asia/Ho_Chi_Minh',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id),
  name text not null,
  description text,
  target_score numeric(5,2) check (target_score is null or (target_score >= 0 and target_score <= 100)),
  exam_date date,
  weekly_study_minutes integer check (weekly_study_minutes is null or weekly_study_minutes > 0),
  status text not null default 'active' check (status in ('active','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.project_members (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  role text not null check (role in ('owner','member')),
  joined_at timestamptz not null default now(),
  unique(project_id, user_id)
);

create unique index if not exists project_members_one_owner_idx
  on public.project_members(project_id) where role='owner';

create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  created_by uuid not null references public.users(id),
  active_version_id uuid,
  display_name text not null,
  status text not null default 'active' check (status in ('active','deleting')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.document_versions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  project_id uuid not null references public.projects(id) on delete cascade,
  version_number integer not null check (version_number > 0),
  storage_path text not null unique,
  original_filename text not null,
  mime_type text not null,
  file_size integer not null check (file_size > 0),
  page_count integer,
  sha256 text not null,
  status text not null default 'pending' check (status in ('pending','processing','ready','error','superseded')),
  summary text,
  summary_status text,
  embedding_model text,
  chunker_version text,
  error_code text,
  error_message text,
  created_at timestamptz not null default now(),
  processed_at timestamptz,
  unique(document_id, version_number),
  unique(document_id, sha256)
);

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname='documents_active_version_id_fkey'
  ) then
    alter table public.documents
      add constraint documents_active_version_id_fkey
      foreign key (active_version_id) references public.document_versions(id) on delete set null;
  end if;
end $$;

create table if not exists public.document_jobs (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null,
  document_version_id uuid references public.document_versions(id) on delete set null,
  job_type text not null check (job_type in ('ingest','delete')),
  status text not null default 'queued' check (status in ('queued','running','succeeded','failed','cancelled')),
  stage text,
  progress_current integer not null default 0,
  progress_total integer not null default 0,
  attempt_count integer not null default 0,
  max_attempts integer not null default 3,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.chunks (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  document_id uuid not null references public.documents(id) on delete cascade,
  document_version_id uuid not null references public.document_versions(id) on delete cascade,
  content text not null,
  embedding vector(384) not null,
  page_number integer,
  section_title text,
  chunk_index integer not null,
  source_spans jsonb,
  token_count integer,
  created_at timestamptz not null default now(),
  unique(document_version_id, chunk_index)
);

create index if not exists chunks_project_id_idx on public.chunks(project_id);
create index if not exists chunks_document_version_id_idx on public.chunks(document_version_id);
create index if not exists chunks_embedding_hnsw_idx
  on public.chunks using hnsw (embedding vector_cosine_ops);

create table if not exists public.chat_sessions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  title text not null default 'New conversation',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists chat_sessions_project_user_idx
  on public.chat_sessions(project_id, user_id);

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.chat_sessions(id) on delete cascade,
  role text not null check (role in ('user','assistant','system')),
  content text not null,
  status text not null default 'delivered',
  citations jsonb,
  retrieval_params jsonb,
  model_name text,
  prompt_version text,
  request_id uuid,
  created_at timestamptz not null default now()
);

create index if not exists chat_messages_session_created_idx
  on public.chat_messages(session_id, created_at);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users(id, email, full_name)
  values (
    new.id,
    coalesce(new.email, new.id::text || '@local.invalid'),
    nullif(new.raw_user_meta_data->>'full_name','')
  )
  on conflict (id) do update set
    email = excluded.email,
    full_name = coalesce(excluded.full_name, public.users.full_name),
    updated_at = now();
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert or update of email, raw_user_meta_data on auth.users
for each row execute function public.handle_new_user();

insert into public.users(id, email, full_name)
select id, coalesce(email, id::text || '@local.invalid'), nullif(raw_user_meta_data->>'full_name','')
from auth.users
on conflict (id) do nothing;

create or replace function public.create_project_with_owner(
  p_owner_id uuid,
  p_name text,
  p_description text default null,
  p_target_score numeric default null,
  p_exam_date date default null,
  p_weekly_study_minutes integer default null
)
returns public.projects
language plpgsql
security definer
set search_path = public
as $$
declare
  v_project public.projects;
begin
  insert into public.projects(owner_id, name, description, target_score, exam_date, weekly_study_minutes)
  values (p_owner_id, p_name, p_description, p_target_score, p_exam_date, p_weekly_study_minutes)
  returning * into v_project;

  insert into public.project_members(project_id, user_id, role)
  values (v_project.id, p_owner_id, 'owner');

  return v_project;
end;
$$;

create or replace function public.match_chunks(
  filter_project_id uuid,
  query_embedding vector(384),
  match_count integer default 5,
  match_threshold double precision default 0.30
)
returns table (
  id uuid,
  content text,
  page_number integer,
  chunk_index integer,
  document_id uuid,
  document_version_id uuid,
  source_file text,
  similarity double precision
)
language sql
stable
as $$
  select
    c.id,
    c.content,
    c.page_number,
    c.chunk_index,
    c.document_id,
    c.document_version_id,
    dv.original_filename as source_file,
    1 - (c.embedding <=> query_embedding) as similarity
  from public.chunks c
  join public.documents d on d.id = c.document_id
  join public.document_versions dv on dv.id = c.document_version_id
  where c.project_id = filter_project_id
    and d.project_id = filter_project_id
    and d.status = 'active'
    and d.active_version_id = c.document_version_id
    and dv.status = 'ready'
    and 1 - (c.embedding <=> query_embedding) >= match_threshold
  order by c.embedding <=> query_embedding
  limit greatest(match_count, 0);
$$;

alter table public.users enable row level security;
alter table public.projects enable row level security;
alter table public.project_members enable row level security;
alter table public.documents enable row level security;
alter table public.document_versions enable row level security;
alter table public.document_jobs enable row level security;
alter table public.chunks enable row level security;
alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;

insert into storage.buckets(id, name, public)
values ('documents', 'documents', false)
on conflict (id) do update set public=false;
