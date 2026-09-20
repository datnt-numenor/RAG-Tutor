-- Harden production RAG core functions and add FK indexes.

alter function public.match_chunks(uuid, vector, integer, double precision)
  set search_path = public;

revoke all on function public.handle_new_user() from public, anon, authenticated;
revoke all on function public.create_project_with_owner(uuid, text, text, numeric, date, integer)
  from public, anon, authenticated;
grant execute on function public.create_project_with_owner(uuid, text, text, numeric, date, integer)
  to service_role;

create index if not exists projects_owner_id_idx on public.projects(owner_id);
create index if not exists project_members_user_id_idx on public.project_members(user_id);
create index if not exists documents_project_id_idx on public.documents(project_id);
create index if not exists documents_created_by_idx on public.documents(created_by);
create index if not exists documents_active_version_id_idx on public.documents(active_version_id);
create index if not exists document_versions_project_id_idx on public.document_versions(project_id);
create index if not exists document_jobs_document_version_id_idx on public.document_jobs(document_version_id);
create index if not exists chunks_document_id_idx on public.chunks(document_id);
create index if not exists chat_sessions_user_id_idx on public.chat_sessions(user_id);
