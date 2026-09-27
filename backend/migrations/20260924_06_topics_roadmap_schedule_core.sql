-- Topics, prerequisites, personalized roadmap and study schedule core.

create table if not exists public.topics (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  name text not null,
  description text,
  difficulty text check (difficulty is null or difficulty in ('basic','intermediate','advanced')),
  bloom_level text check (
    bloom_level is null or bloom_level in ('remember','understand','apply','analyze')
  ),
  is_core boolean not null default false,
  model_name text,
  prompt_version text,
  created_at timestamptz not null default now()
);

create unique index if not exists topics_project_name_unique
  on public.topics(project_id, lower(name));

create table if not exists public.topic_sources (
  topic_id uuid not null references public.topics(id) on delete cascade,
  chunk_id uuid not null references public.chunks(id) on delete cascade,
  relevance numeric(4,3) not null default 1.0,
  primary key (topic_id, chunk_id)
);

create table if not exists public.topic_prerequisites (
  topic_id uuid not null references public.topics(id) on delete cascade,
  prerequisite_topic_id uuid not null references public.topics(id) on delete cascade,
  strength numeric(4,3) not null default 1.0,
  primary key (topic_id, prerequisite_topic_id),
  check (topic_id <> prerequisite_topic_id)
);

create table if not exists public.schedules (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  created_by uuid not null references public.users(id) on delete cascade,
  topic_id uuid references public.topics(id) on delete set null,
  title text not null,
  description text,
  start_time timestamptz not null,
  end_time timestamptz,
  event_type text not null check (event_type in ('study','quiz','review','deadline')),
  source text not null default 'manual' check (source in ('manual','ai_suggested')),
  suggestion_status text not null default 'accepted'
    check (suggestion_status in ('suggested','accepted','rejected')),
  created_at timestamptz not null default now()
);

create table if not exists public.schedule_completions (
  id uuid primary key default gen_random_uuid(),
  schedule_id uuid not null references public.schedules(id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  completed_at timestamptz not null default now(),
  note text,
  unique(schedule_id, user_id)
);

alter table public.questions
  add column if not exists topic_id uuid references public.topics(id) on delete set null;

create index if not exists topics_project_id_idx on public.topics(project_id);
create index if not exists topic_sources_chunk_id_idx on public.topic_sources(chunk_id);
create index if not exists topic_prerequisites_prereq_idx on public.topic_prerequisites(prerequisite_topic_id);
create index if not exists schedules_project_start_idx on public.schedules(project_id, start_time);
create index if not exists schedule_completions_user_idx on public.schedule_completions(user_id);

alter table public.topics enable row level security;
alter table public.topic_sources enable row level security;
alter table public.topic_prerequisites enable row level security;
alter table public.schedules enable row level security;
alter table public.schedule_completions enable row level security;
