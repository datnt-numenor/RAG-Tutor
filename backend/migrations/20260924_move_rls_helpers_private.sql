-- Move RLS helper functions out of exposed public schema and update policies.

grant usage on schema private to authenticated, service_role;
grant execute on function private.is_project_member(uuid) to authenticated, service_role;
grant execute on function private.is_project_owner(uuid) to authenticated, service_role;

alter policy projects_select_member on public.projects using (private.is_project_member(id));
alter policy projects_update_owner on public.projects using (private.is_project_owner(id)) with check (owner_id = auth.uid());
alter policy projects_delete_owner on public.projects using (private.is_project_owner(id));

alter policy project_members_select_member on public.project_members using (private.is_project_member(project_id));
alter policy project_members_insert_owner on public.project_members with check (private.is_project_owner(project_id) or (user_id = auth.uid() and role = 'owner'));
alter policy project_members_update_owner on public.project_members using (private.is_project_owner(project_id)) with check (private.is_project_owner(project_id));
alter policy project_members_delete_owner on public.project_members using (private.is_project_owner(project_id));

alter policy documents_select_member on public.documents using (private.is_project_member(project_id));
alter policy documents_write_owner on public.documents using (private.is_project_owner(project_id)) with check (private.is_project_owner(project_id));
alter policy document_versions_select_member on public.document_versions using (private.is_project_member(project_id));
alter policy document_versions_write_owner on public.document_versions using (private.is_project_owner(project_id)) with check (private.is_project_owner(project_id));
alter policy document_jobs_select_member on public.document_jobs using (private.is_project_member(project_id));
alter policy document_jobs_write_owner on public.document_jobs using (private.is_project_owner(project_id)) with check (private.is_project_owner(project_id));
alter policy chunks_select_member on public.chunks using (private.is_project_member(project_id));
alter policy chunks_write_owner on public.chunks using (private.is_project_owner(project_id)) with check (private.is_project_owner(project_id));

alter policy chat_sessions_select_own on public.chat_sessions using (user_id = auth.uid() and private.is_project_member(project_id));
alter policy chat_sessions_insert_own on public.chat_sessions with check (user_id = auth.uid() and private.is_project_member(project_id));
alter policy chat_sessions_update_own on public.chat_sessions using (user_id = auth.uid() and private.is_project_member(project_id)) with check (user_id = auth.uid() and private.is_project_member(project_id));
alter policy chat_sessions_delete_own on public.chat_sessions using (user_id = auth.uid() and private.is_project_member(project_id));

alter policy questions_select_member on public.questions using (private.is_project_member(project_id));
alter policy questions_write_owner on public.questions using (private.is_project_owner(project_id)) with check (private.is_project_owner(project_id));
alter policy quiz_sessions_own on public.quiz_sessions using (user_id = auth.uid() and private.is_project_member(project_id)) with check (user_id = auth.uid() and private.is_project_member(project_id));
alter policy quiz_attempts_own on public.quiz_attempts using (user_id = auth.uid() and private.is_project_member(project_id)) with check (user_id = auth.uid() and private.is_project_member(project_id));
alter policy review_states_own on public.review_states using (user_id = auth.uid() and private.is_project_member(project_id)) with check (user_id = auth.uid() and private.is_project_member(project_id));

alter policy invitations_select_owner on public.project_invitations using (private.is_project_owner(project_id));
alter policy invitations_write_owner on public.project_invitations using (private.is_project_owner(project_id)) with check (private.is_project_owner(project_id));
alter policy notes_own on public.notes using (user_id = auth.uid() and private.is_project_member(project_id)) with check (user_id = auth.uid() and private.is_project_member(project_id));

alter policy topics_select_member on public.topics using (private.is_project_member(project_id));
alter policy topics_write_owner on public.topics using (private.is_project_owner(project_id)) with check (private.is_project_owner(project_id));
alter policy schedules_select_member on public.schedules using (private.is_project_member(project_id));
alter policy schedules_write_owner on public.schedules using (private.is_project_owner(project_id)) with check (private.is_project_owner(project_id));

alter policy study_events_own on public.study_events using (user_id = auth.uid() and private.is_project_member(project_id)) with check (user_id = auth.uid() and private.is_project_member(project_id));
alter policy progress_snapshots_own on public.progress_snapshots using (user_id = auth.uid() and private.is_project_member(project_id)) with check (user_id = auth.uid() and private.is_project_member(project_id));

revoke execute on function public.is_project_member(uuid, uuid) from anon, authenticated, service_role, public;
revoke execute on function public.is_project_owner(uuid, uuid) from anon, authenticated, service_role, public;
drop function public.is_project_member(uuid, uuid);
drop function public.is_project_owner(uuid, uuid);
