-- Raw study events + idempotent daily progress snapshots.
set search_path = public, extensions;

create table if not exists public.study_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  project_id uuid not null references public.projects(id) on delete cascade,
  topic_id uuid references public.topics(id) on delete set null,
  event_type text not null,
  duration_seconds integer,
  occurred_at timestamptz not null default now(),
  source_id uuid,
  idempotency_key text unique,
  metadata jsonb
);

create table if not exists public.progress_snapshots (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  project_id uuid not null references public.projects(id) on delete cascade,
  snapshot_date date not null,
  questions_attempted integer not null default 0,
  questions_correct integer not null default 0,
  avg_score numeric(5,2) not null default 0,
  topics_covered integer not null default 0,
  study_minutes integer not null default 0,
  created_at timestamptz not null default now(),
  unique(user_id, project_id, snapshot_date)
);

create index if not exists study_events_user_project_time_idx
  on public.study_events(user_id, project_id, occurred_at);

create index if not exists progress_snapshots_user_date_idx
  on public.progress_snapshots(user_id, snapshot_date);

alter table public.study_events enable row level security;
alter table public.progress_snapshots enable row level security;

drop policy if exists study_events_select_own on public.study_events;
create policy study_events_select_own on public.study_events
for select to authenticated
using (
  user_id = auth.uid()
  and private.is_project_member(project_id)
);

drop policy if exists study_events_write_own on public.study_events;
create policy study_events_write_own on public.study_events
for all to authenticated
using (
  user_id = auth.uid()
  and private.is_project_member(project_id)
)
with check (
  user_id = auth.uid()
  and private.is_project_member(project_id)
);

drop policy if exists progress_snapshots_select_own on public.progress_snapshots;
create policy progress_snapshots_select_own on public.progress_snapshots
for select to authenticated
using (
  user_id = auth.uid()
  and private.is_project_member(project_id)
);

drop policy if exists progress_snapshots_write_own on public.progress_snapshots;
create policy progress_snapshots_write_own on public.progress_snapshots
for all to authenticated
using (
  user_id = auth.uid()
  and private.is_project_member(project_id)
)
with check (
  user_id = auth.uid()
  and private.is_project_member(project_id)
);
