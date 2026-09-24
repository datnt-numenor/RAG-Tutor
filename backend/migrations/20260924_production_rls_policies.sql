-- Production RLS policies. Backend service_role bypasses RLS, while direct authenticated access is tenant-scoped.

create or replace function public.is_project_member(p_project_id uuid, p_user_id uuid default auth.uid())
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.project_members pm
    where pm.project_id = p_project_id and pm.user_id = p_user_id
  );
$$;

create or replace function public.is_project_owner(p_project_id uuid, p_user_id uuid default auth.uid())
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.project_members pm
    where pm.project_id = p_project_id
      and pm.user_id = p_user_id
      and pm.role = 'owner'
  );
$$;

revoke all on function public.is_project_member(uuid, uuid) from public;
revoke all on function public.is_project_owner(uuid, uuid) from public;
grant execute on function public.is_project_member(uuid, uuid) to authenticated, service_role;
grant execute on function public.is_project_owner(uuid, uuid) to authenticated, service_role;

create policy users_select_own on public.users for select to authenticated using (id = auth.uid());
create policy users_update_own on public.users for update to authenticated using (id = auth.uid()) with check (id = auth.uid());

create policy projects_select_member on public.projects for select to authenticated using (public.is_project_member(id));
create policy projects_insert_owner on public.projects for insert to authenticated with check (owner_id = auth.uid());
create policy projects_update_owner on public.projects for update to authenticated using (public.is_project_owner(id)) with check (owner_id = auth.uid());
create policy projects_delete_owner on public.projects for delete to authenticated using (public.is_project_owner(id));

create policy project_members_select_member on public.project_members for select to authenticated using (public.is_project_member(project_id));
create policy project_members_insert_owner on public.project_members for insert to authenticated with check (public.is_project_owner(project_id) or (user_id = auth.uid() and role = 'owner'));
create policy project_members_update_owner on public.project_members for update to authenticated using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));
create policy project_members_delete_owner on public.project_members for delete to authenticated using (public.is_project_owner(project_id));

create policy documents_select_member on public.documents for select to authenticated using (public.is_project_member(project_id));
create policy documents_write_owner on public.documents for all to authenticated using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));

create policy document_versions_select_member on public.document_versions for select to authenticated using (public.is_project_member(project_id));
create policy document_versions_write_owner on public.document_versions for all to authenticated using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));

create policy document_jobs_select_member on public.document_jobs for select to authenticated using (public.is_project_member(project_id));
create policy document_jobs_write_owner on public.document_jobs for all to authenticated using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));

create policy chunks_select_member on public.chunks for select to authenticated using (public.is_project_member(project_id));
create policy chunks_write_owner on public.chunks for all to authenticated using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));

create policy chat_sessions_select_own on public.chat_sessions for select to authenticated using (user_id = auth.uid() and public.is_project_member(project_id));
create policy chat_sessions_insert_own on public.chat_sessions for insert to authenticated with check (user_id = auth.uid() and public.is_project_member(project_id));
create policy chat_sessions_update_own on public.chat_sessions for update to authenticated using (user_id = auth.uid() and public.is_project_member(project_id)) with check (user_id = auth.uid() and public.is_project_member(project_id));
create policy chat_sessions_delete_own on public.chat_sessions for delete to authenticated using (user_id = auth.uid() and public.is_project_member(project_id));

create policy chat_messages_select_own on public.chat_messages for select to authenticated using (
  exists (select 1 from public.chat_sessions cs where cs.id = session_id and cs.user_id = auth.uid() and public.is_project_member(cs.project_id))
);
create policy chat_messages_insert_own on public.chat_messages for insert to authenticated with check (
  exists (select 1 from public.chat_sessions cs where cs.id = session_id and cs.user_id = auth.uid() and public.is_project_member(cs.project_id))
);

create policy questions_select_member on public.questions for select to authenticated using (public.is_project_member(project_id));
create policy questions_write_owner on public.questions for all to authenticated using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));
create policy question_sources_select_member on public.question_sources for select to authenticated using (
  exists (select 1 from public.questions q where q.id = question_id and public.is_project_member(q.project_id))
);
create policy question_sources_write_owner on public.question_sources for all to authenticated using (
  exists (select 1 from public.questions q where q.id = question_id and public.is_project_owner(q.project_id))
) with check (
  exists (select 1 from public.questions q where q.id = question_id and public.is_project_owner(q.project_id))
);

create policy quiz_sessions_own on public.quiz_sessions for all to authenticated using (user_id = auth.uid() and public.is_project_member(project_id)) with check (user_id = auth.uid() and public.is_project_member(project_id));
create policy quiz_attempts_own on public.quiz_attempts for all to authenticated using (user_id = auth.uid() and public.is_project_member(project_id)) with check (user_id = auth.uid() and public.is_project_member(project_id));
create policy review_states_own on public.review_states for all to authenticated using (user_id = auth.uid() and public.is_project_member(project_id)) with check (user_id = auth.uid() and public.is_project_member(project_id));

create policy invitations_select_owner on public.project_invitations for select to authenticated using (public.is_project_owner(project_id));
create policy invitations_write_owner on public.project_invitations for all to authenticated using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));

create policy notes_own on public.notes for all to authenticated using (user_id = auth.uid() and public.is_project_member(project_id)) with check (user_id = auth.uid() and public.is_project_member(project_id));

create policy topics_select_member on public.topics for select to authenticated using (public.is_project_member(project_id));
create policy topics_write_owner on public.topics for all to authenticated using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));
create policy topic_sources_select_member on public.topic_sources for select to authenticated using (
  exists (select 1 from public.topics t where t.id = topic_id and public.is_project_member(t.project_id))
);
create policy topic_sources_write_owner on public.topic_sources for all to authenticated using (
  exists (select 1 from public.topics t where t.id = topic_id and public.is_project_owner(t.project_id))
) with check (
  exists (select 1 from public.topics t where t.id = topic_id and public.is_project_owner(t.project_id))
);
create policy topic_prereqs_select_member on public.topic_prerequisites for select to authenticated using (
  exists (select 1 from public.topics t where t.id = topic_id and public.is_project_member(t.project_id))
);
create policy topic_prereqs_write_owner on public.topic_prerequisites for all to authenticated using (
  exists (select 1 from public.topics t where t.id = topic_id and public.is_project_owner(t.project_id))
) with check (
  exists (select 1 from public.topics t where t.id = topic_id and public.is_project_owner(t.project_id))
);

create policy schedules_select_member on public.schedules for select to authenticated using (public.is_project_member(project_id));
create policy schedules_write_owner on public.schedules for all to authenticated using (public.is_project_owner(project_id)) with check (public.is_project_owner(project_id));
create policy schedule_completions_own on public.schedule_completions for all to authenticated using (
  user_id = auth.uid() and exists (select 1 from public.schedules s where s.id = schedule_id and public.is_project_member(s.project_id))
) with check (
  user_id = auth.uid() and exists (select 1 from public.schedules s where s.id = schedule_id and public.is_project_member(s.project_id))
);

create policy study_events_own on public.study_events for all to authenticated using (user_id = auth.uid() and public.is_project_member(project_id)) with check (user_id = auth.uid() and public.is_project_member(project_id));
create policy progress_snapshots_own on public.progress_snapshots for all to authenticated using (user_id = auth.uid() and public.is_project_member(project_id)) with check (user_id = auth.uid() and public.is_project_member(project_id));
