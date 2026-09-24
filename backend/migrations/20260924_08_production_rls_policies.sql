-- Production RLS policies. Backend service_role still performs system actions,
-- while direct authenticated Supabase access remains tenant-isolated.

create or replace function public.is_project_member(p_project_id uuid)
returns boolean
language sql stable security definer
set search_path = public
as $$
  select exists (
    select 1 from public.project_members pm
    where pm.project_id = p_project_id
      and pm.user_id = auth.uid()
  );
$$;

create or replace function public.is_project_owner(p_project_id uuid)
returns boolean
language sql stable security definer
set search_path = public
as $$
  select exists (
    select 1 from public.project_members pm
    where pm.project_id = p_project_id
      and pm.user_id = auth.uid()
      and pm.role = 'owner'
  );
$$;

grant execute on function public.is_project_member(uuid) to authenticated;
grant execute on function public.is_project_owner(uuid) to authenticated;

drop policy if exists users_select_self on public.users;
create policy users_select_self on public.users for select to authenticated
using (id = auth.uid());

drop policy if exists users_update_self on public.users;
create policy users_update_self on public.users for update to authenticated
using (id = auth.uid()) with check (id = auth.uid());

drop policy if exists projects_select_member on public.projects;
create policy projects_select_member on public.projects for select to authenticated
using (public.is_project_member(id));

drop policy if exists projects_update_owner on public.projects;
create policy projects_update_owner on public.projects for update to authenticated
using (public.is_project_owner(id)) with check (public.is_project_owner(id));

drop policy if exists project_members_select_member on public.project_members;
create policy project_members_select_member on public.project_members for select to authenticated
using (public.is_project_member(project_id));

drop policy if exists documents_select_member on public.documents;
create policy documents_select_member on public.documents for select to authenticated
using (public.is_project_member(project_id));

drop policy if exists documents_write_owner on public.documents;
create policy documents_write_owner on public.documents for all to authenticated
using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));

drop policy if exists document_versions_select_member on public.document_versions;
create policy document_versions_select_member on public.document_versions for select to authenticated
using (public.is_project_member(project_id));

drop policy if exists document_versions_write_owner on public.document_versions;
create policy document_versions_write_owner on public.document_versions for all to authenticated
using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));

drop policy if exists document_jobs_select_member on public.document_jobs;
create policy document_jobs_select_member on public.document_jobs for select to authenticated
using (public.is_project_member(project_id));

drop policy if exists document_jobs_write_owner on public.document_jobs;
create policy document_jobs_write_owner on public.document_jobs for all to authenticated
using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));

drop policy if exists chunks_select_member on public.chunks;
create policy chunks_select_member on public.chunks for select to authenticated
using (public.is_project_member(project_id));

drop policy if exists chat_sessions_select_own on public.chat_sessions;
create policy chat_sessions_select_own on public.chat_sessions for select to authenticated
using (user_id = auth.uid() and public.is_project_member(project_id));

drop policy if exists chat_sessions_write_own on public.chat_sessions;
create policy chat_sessions_write_own on public.chat_sessions for all to authenticated
using (user_id = auth.uid() and public.is_project_member(project_id))
with check (user_id = auth.uid() and public.is_project_member(project_id));

drop policy if exists chat_messages_select_own_session on public.chat_messages;
create policy chat_messages_select_own_session on public.chat_messages for select to authenticated
using (exists (
  select 1 from public.chat_sessions cs
  where cs.id = chat_messages.session_id
    and cs.user_id = auth.uid()
    and public.is_project_member(cs.project_id)
));

drop policy if exists chat_messages_write_own_session on public.chat_messages;
create policy chat_messages_write_own_session on public.chat_messages for all to authenticated
using (exists (
  select 1 from public.chat_sessions cs
  where cs.id = chat_messages.session_id
    and cs.user_id = auth.uid()
    and public.is_project_member(cs.project_id)
))
with check (exists (
  select 1 from public.chat_sessions cs
  where cs.id = chat_messages.session_id
    and cs.user_id = auth.uid()
    and public.is_project_member(cs.project_id)
));

drop policy if exists questions_select_member on public.questions;
create policy questions_select_member on public.questions for select to authenticated
using (public.is_project_member(project_id));

drop policy if exists questions_write_owner on public.questions;
create policy questions_write_owner on public.questions for all to authenticated
using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));

drop policy if exists question_sources_select_member on public.question_sources;
create policy question_sources_select_member on public.question_sources for select to authenticated
using (exists (
  select 1 from public.questions q
  where q.id = question_sources.question_id
    and public.is_project_member(q.project_id)
));

drop policy if exists quiz_sessions_select_own on public.quiz_sessions;
create policy quiz_sessions_select_own on public.quiz_sessions for select to authenticated
using (user_id = auth.uid() and public.is_project_member(project_id));

drop policy if exists quiz_sessions_write_own on public.quiz_sessions;
create policy quiz_sessions_write_own on public.quiz_sessions for all to authenticated
using (user_id = auth.uid() and public.is_project_member(project_id))
with check (user_id = auth.uid() and public.is_project_member(project_id));

drop policy if exists quiz_attempts_select_own on public.quiz_attempts;
create policy quiz_attempts_select_own on public.quiz_attempts for select to authenticated
using (user_id = auth.uid() and public.is_project_member(project_id));

drop policy if exists quiz_attempts_write_own on public.quiz_attempts;
create policy quiz_attempts_write_own on public.quiz_attempts for all to authenticated
using (user_id = auth.uid() and public.is_project_member(project_id))
with check (user_id = auth.uid() and public.is_project_member(project_id));

drop policy if exists review_states_select_own on public.review_states;
create policy review_states_select_own on public.review_states for select to authenticated
using (user_id = auth.uid() and public.is_project_member(project_id));

drop policy if exists review_states_write_own on public.review_states;
create policy review_states_write_own on public.review_states for all to authenticated
using (user_id = auth.uid() and public.is_project_member(project_id))
with check (user_id = auth.uid() and public.is_project_member(project_id));

drop policy if exists topics_select_member on public.topics;
create policy topics_select_member on public.topics for select to authenticated
using (public.is_project_member(project_id));

drop policy if exists topics_write_owner on public.topics;
create policy topics_write_owner on public.topics for all to authenticated
using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));

drop policy if exists topic_sources_select_member on public.topic_sources;
create policy topic_sources_select_member on public.topic_sources for select to authenticated
using (exists (
  select 1 from public.topics t
  where t.id = topic_sources.topic_id
    and public.is_project_member(t.project_id)
));

drop policy if exists topic_prerequisites_select_member on public.topic_prerequisites;
create policy topic_prerequisites_select_member on public.topic_prerequisites for select to authenticated
using (exists (
  select 1 from public.topics t
  where t.id = topic_prerequisites.topic_id
    and public.is_project_member(t.project_id)
));

drop policy if exists schedules_select_member on public.schedules;
create policy schedules_select_member on public.schedules for select to authenticated
using (public.is_project_member(project_id));

drop policy if exists schedules_write_owner on public.schedules;
create policy schedules_write_owner on public.schedules for all to authenticated
using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));

drop policy if exists schedule_completions_select_own on public.schedule_completions;
create policy schedule_completions_select_own on public.schedule_completions for select to authenticated
using (user_id = auth.uid());

drop policy if exists schedule_completions_write_own on public.schedule_completions;
create policy schedule_completions_write_own on public.schedule_completions for all to authenticated
using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists notes_select_own on public.notes;
create policy notes_select_own on public.notes for select to authenticated
using (user_id = auth.uid() and public.is_project_member(project_id));

drop policy if exists notes_write_own on public.notes;
create policy notes_write_own on public.notes for all to authenticated
using (user_id = auth.uid() and public.is_project_member(project_id))
with check (user_id = auth.uid() and public.is_project_member(project_id));

drop policy if exists project_invitations_select_owner on public.project_invitations;
create policy project_invitations_select_owner on public.project_invitations for select to authenticated
using (public.is_project_owner(project_id));

drop policy if exists project_invitations_write_owner on public.project_invitations;
create policy project_invitations_write_owner on public.project_invitations for all to authenticated
using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));
