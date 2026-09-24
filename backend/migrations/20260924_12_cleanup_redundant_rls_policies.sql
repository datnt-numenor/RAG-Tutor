-- Cleanup for environments that received the temporary interactive RLS pass.
-- Safe on fresh installs: every extra policy is dropped with IF EXISTS and
-- canonical policies are restored with the same semantics as the ordered RLS migrations.

drop policy if exists users_select_own on public.users;
drop policy if exists users_update_own on public.users;

drop policy if exists projects_insert_owner on public.projects;
drop policy if exists projects_delete_owner on public.projects;

drop policy if exists project_members_insert_owner on public.project_members;
drop policy if exists project_members_update_owner on public.project_members;
drop policy if exists project_members_delete_owner on public.project_members;

drop policy if exists documents_write_owner on public.documents;
drop policy if exists document_versions_write_owner on public.document_versions;
drop policy if exists document_jobs_write_owner on public.document_jobs;
drop policy if exists chunks_write_owner on public.chunks;

drop policy if exists chat_messages_select_own on public.chat_messages;
drop policy if exists chat_messages_insert_own on public.chat_messages;

drop policy if exists questions_write_owner on public.questions;
drop policy if exists question_sources_write_owner on public.question_sources;

drop policy if exists quiz_sessions_own on public.quiz_sessions;
drop policy if exists quiz_attempts_own on public.quiz_attempts;
drop policy if exists review_states_own on public.review_states;

drop policy if exists invitations_select_owner on public.project_invitations;
drop policy if exists invitations_write_owner on public.project_invitations;

drop policy if exists notes_own on public.notes;

drop policy if exists topics_write_owner on public.topics;
drop policy if exists topic_sources_write_owner on public.topic_sources;
drop policy if exists topic_prereqs_select_member on public.topic_prerequisites;
drop policy if exists topic_prereqs_write_owner on public.topic_prerequisites;

drop policy if exists schedules_write_owner on public.schedules;
drop policy if exists schedule_completions_own on public.schedule_completions;
drop policy if exists study_events_own on public.study_events;
drop policy if exists progress_snapshots_own on public.progress_snapshots;

drop policy if exists projects_update_owner on public.projects;
create policy projects_update_owner on public.projects
for update to authenticated
using (private.is_project_owner(id))
with check (private.is_project_owner(id));

drop policy if exists chat_sessions_select_own on public.chat_sessions;
create policy chat_sessions_select_own on public.chat_sessions
for select to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);

drop policy if exists chat_sessions_insert_own on public.chat_sessions;
create policy chat_sessions_insert_own on public.chat_sessions
for insert to authenticated
with check (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);

drop policy if exists chat_sessions_update_own on public.chat_sessions;
create policy chat_sessions_update_own on public.chat_sessions
for update to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
)
with check (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);

drop policy if exists chat_sessions_delete_own on public.chat_sessions;
create policy chat_sessions_delete_own on public.chat_sessions
for delete to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
