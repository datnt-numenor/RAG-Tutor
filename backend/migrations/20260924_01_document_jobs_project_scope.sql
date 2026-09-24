-- Scope document jobs to a project so authorization and history survive document deletion.

alter table public.document_jobs
  add column if not exists project_id uuid;

update public.document_jobs j
set project_id = coalesce(
  (
    select dv.project_id
    from public.document_versions dv
    where dv.id = j.document_version_id
  ),
  (
    select d.project_id
    from public.documents d
    where d.id = j.document_id
  )
)
where j.project_id is null;

alter table public.document_jobs
  alter column project_id set not null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'document_jobs_project_id_fkey'
  ) then
    alter table public.document_jobs
      add constraint document_jobs_project_id_fkey
      foreign key (project_id)
      references public.projects(id)
      on delete cascade;
  end if;
end $$;

create index if not exists document_jobs_project_id_idx
  on public.document_jobs(project_id);
