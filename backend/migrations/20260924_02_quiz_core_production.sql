-- Production quiz core for RAG-grounded question generation and spaced review.

create table if not exists public.questions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  question_type text not null check (question_type in ('mcq','essay')),
  question_text text not null,
  options jsonb,
  correct_answer text,
  model_answer text,
  key_points jsonb,
  rubric jsonb,
  max_score numeric(6,2) not null default 1.0,
  status text not null default 'active' check (status in ('active','retired')),
  version integer not null default 1,
  model_name text,
  prompt_version text,
  created_at timestamptz not null default now()
);

create table if not exists public.question_sources (
  question_id uuid not null references public.questions(id) on delete cascade,
  chunk_id uuid not null references public.chunks(id) on delete cascade,
  primary key (question_id, chunk_id)
);

create table if not exists public.quiz_sessions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  status text not null default 'in_progress'
    check (status in ('in_progress','submitted','graded','abandoned')),
  question_ids uuid[] not null,
  total_score numeric(8,2),
  max_score numeric(8,2),
  started_at timestamptz not null default now(),
  submitted_at timestamptz,
  graded_at timestamptz
);

create table if not exists public.quiz_attempts (
  id uuid primary key default gen_random_uuid(),
  quiz_session_id uuid not null references public.quiz_sessions(id) on delete cascade,
  question_id uuid references public.questions(id) on delete set null,
  user_id uuid not null references public.users(id) on delete cascade,
  project_id uuid not null references public.projects(id) on delete cascade,
  question_text_snapshot text not null,
  options_snapshot jsonb,
  max_score_snapshot numeric(6,2) not null,
  user_answer text,
  score numeric(6,2),
  is_correct boolean,
  feedback text,
  grading_method text,
  model_name text,
  prompt_version text,
  status text not null default 'draft'
    check (status in ('draft','submitted','graded','error')),
  submitted_at timestamptz,
  graded_at timestamptz
);

create table if not exists public.review_states (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  question_id uuid not null references public.questions(id) on delete cascade,
  project_id uuid not null references public.projects(id) on delete cascade,
  due_at timestamptz not null,
  interval_days integer not null default 1,
  repetitions integer not null default 0,
  ease_factor numeric(4,2) not null default 2.5,
  last_score numeric(4,2),
  last_reviewed_at timestamptz,
  unique(user_id, question_id)
);

create index if not exists questions_project_id_idx on public.questions(project_id);
create index if not exists question_sources_chunk_id_idx on public.question_sources(chunk_id);
create index if not exists quiz_sessions_project_user_idx on public.quiz_sessions(project_id, user_id);
create index if not exists quiz_attempts_session_idx on public.quiz_attempts(quiz_session_id);
create index if not exists review_states_due_idx on public.review_states(user_id, project_id, due_at);

alter table public.questions enable row level security;
alter table public.question_sources enable row level security;
alter table public.quiz_sessions enable row level security;
alter table public.quiz_attempts enable row level security;
alter table public.review_states enable row level security;
