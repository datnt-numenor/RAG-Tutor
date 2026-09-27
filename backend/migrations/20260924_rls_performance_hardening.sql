-- Performance hardening for RLS and foreign-key access paths.
-- Keeps authorization semantics unchanged while avoiding per-row auth.uid()
-- re-evaluation and overlapping permissive SELECT policies.

create index if not exists notes_document_version_id_idx on public.notes(document_version_id);
create index if not exists notes_project_id_idx on public.notes(project_id);
create index if not exists progress_snapshots_project_id_idx on public.progress_snapshots(project_id);
create index if not exists project_invitations_invited_by_idx on public.project_invitations(invited_by);
create index if not exists questions_topic_id_idx on public.questions(topic_id);
create index if not exists quiz_attempts_project_id_idx on public.quiz_attempts(project_id);
create index if not exists quiz_attempts_question_id_idx on public.quiz_attempts(question_id);
create index if not exists quiz_attempts_user_id_idx on public.quiz_attempts(user_id);
create index if not exists quiz_sessions_user_id_idx on public.quiz_sessions(user_id);
create index if not exists review_states_project_id_idx on public.review_states(project_id);
create index if not exists review_states_question_id_idx on public.review_states(question_id);
create index if not exists schedules_created_by_idx on public.schedules(created_by);
create index if not exists schedules_topic_id_idx on public.schedules(topic_id);
create index if not exists study_events_project_id_idx on public.study_events(project_id);
create index if not exists study_events_topic_id_idx on public.study_events(topic_id);

drop policy if exists users_select_self on public.users;
create policy users_select_self on public.users
for select to authenticated
using (id = (select auth.uid()));

drop policy if exists users_update_self on public.users;
create policy users_update_self on public.users
for update to authenticated
using (id = (select auth.uid()))
with check (id = (select auth.uid()));

drop policy if exists documents_write_owner on public.documents;
create policy documents_insert_owner on public.documents
for insert to authenticated
with check (private.is_project_owner(project_id));
create policy documents_update_owner on public.documents
for update to authenticated
using (private.is_project_owner(project_id))
with check (private.is_project_owner(project_id));
create policy documents_delete_owner on public.documents
for delete to authenticated
using (private.is_project_owner(project_id));

drop policy if exists document_versions_write_owner on public.document_versions;
create policy document_versions_insert_owner on public.document_versions
for insert to authenticated
with check (private.is_project_owner(project_id));
create policy document_versions_update_owner on public.document_versions
for update to authenticated
using (private.is_project_owner(project_id))
with check (private.is_project_owner(project_id));
create policy document_versions_delete_owner on public.document_versions
for delete to authenticated
using (private.is_project_owner(project_id));

drop policy if exists document_jobs_write_owner on public.document_jobs;
create policy document_jobs_insert_owner on public.document_jobs
for insert to authenticated
with check (private.is_project_owner(project_id));
create policy document_jobs_update_owner on public.document_jobs
for update to authenticated
using (private.is_project_owner(project_id))
with check (private.is_project_owner(project_id));
create policy document_jobs_delete_owner on public.document_jobs
for delete to authenticated
using (private.is_project_owner(project_id));

drop policy if exists project_invitations_write_owner on public.project_invitations;
create policy project_invitations_insert_owner on public.project_invitations
for insert to authenticated
with check (private.is_project_owner(project_id));
create policy project_invitations_update_owner on public.project_invitations
for update to authenticated
using (private.is_project_owner(project_id))
with check (private.is_project_owner(project_id));
create policy project_invitations_delete_owner on public.project_invitations
for delete to authenticated
using (private.is_project_owner(project_id));

drop policy if exists questions_write_owner on public.questions;
create policy questions_insert_owner on public.questions
for insert to authenticated
with check (private.is_project_owner(project_id));
create policy questions_update_owner on public.questions
for update to authenticated
using (private.is_project_owner(project_id))
with check (private.is_project_owner(project_id));
create policy questions_delete_owner on public.questions
for delete to authenticated
using (private.is_project_owner(project_id));

drop policy if exists schedules_write_owner on public.schedules;
create policy schedules_insert_owner on public.schedules
for insert to authenticated
with check (private.is_project_owner(project_id));
create policy schedules_update_owner on public.schedules
for update to authenticated
using (private.is_project_owner(project_id))
with check (private.is_project_owner(project_id));
create policy schedules_delete_owner on public.schedules
for delete to authenticated
using (private.is_project_owner(project_id));

drop policy if exists topics_write_owner on public.topics;
create policy topics_insert_owner on public.topics
for insert to authenticated
with check (private.is_project_owner(project_id));
create policy topics_update_owner on public.topics
for update to authenticated
using (private.is_project_owner(project_id))
with check (private.is_project_owner(project_id));
create policy topics_delete_owner on public.topics
for delete to authenticated
using (private.is_project_owner(project_id));

drop policy if exists notes_select_own on public.notes;
create policy notes_select_own on public.notes
for select to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
drop policy if exists notes_write_own on public.notes;
create policy notes_insert_own on public.notes
for insert to authenticated
with check (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
create policy notes_update_own on public.notes
for update to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
)
with check (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
create policy notes_delete_own on public.notes
for delete to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);

drop policy if exists chat_sessions_select_own on public.chat_sessions;
create policy chat_sessions_select_own on public.chat_sessions
for select to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
drop policy if exists chat_sessions_write_own on public.chat_sessions;
create policy chat_sessions_insert_own on public.chat_sessions
for insert to authenticated
with check (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
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
create policy chat_sessions_delete_own on public.chat_sessions
for delete to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);

drop policy if exists quiz_sessions_select_own on public.quiz_sessions;
create policy quiz_sessions_select_own on public.quiz_sessions
for select to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
drop policy if exists quiz_sessions_write_own on public.quiz_sessions;
create policy quiz_sessions_insert_own on public.quiz_sessions
for insert to authenticated
with check (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
create policy quiz_sessions_update_own on public.quiz_sessions
for update to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
)
with check (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
create policy quiz_sessions_delete_own on public.quiz_sessions
for delete to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);

drop policy if exists quiz_attempts_select_own on public.quiz_attempts;
create policy quiz_attempts_select_own on public.quiz_attempts
for select to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
drop policy if exists quiz_attempts_write_own on public.quiz_attempts;
create policy quiz_attempts_insert_own on public.quiz_attempts
for insert to authenticated
with check (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
create policy quiz_attempts_update_own on public.quiz_attempts
for update to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
)
with check (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
create policy quiz_attempts_delete_own on public.quiz_attempts
for delete to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);

drop policy if exists review_states_select_own on public.review_states;
create policy review_states_select_own on public.review_states
for select to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
drop policy if exists review_states_write_own on public.review_states;
create policy review_states_insert_own on public.review_states
for insert to authenticated
with check (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
create policy review_states_update_own on public.review_states
for update to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
)
with check (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
create policy review_states_delete_own on public.review_states
for delete to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);

drop policy if exists progress_snapshots_select_own on public.progress_snapshots;
create policy progress_snapshots_select_own on public.progress_snapshots
for select to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
drop policy if exists progress_snapshots_write_own on public.progress_snapshots;
create policy progress_snapshots_insert_own on public.progress_snapshots
for insert to authenticated
with check (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
create policy progress_snapshots_update_own on public.progress_snapshots
for update to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
)
with check (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
create policy progress_snapshots_delete_own on public.progress_snapshots
for delete to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);

drop policy if exists study_events_select_own on public.study_events;
create policy study_events_select_own on public.study_events
for select to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
drop policy if exists study_events_write_own on public.study_events;
create policy study_events_insert_own on public.study_events
for insert to authenticated
with check (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
create policy study_events_update_own on public.study_events
for update to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
)
with check (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);
create policy study_events_delete_own on public.study_events
for delete to authenticated
using (
  user_id = (select auth.uid())
  and private.is_project_member(project_id)
);

drop policy if exists schedule_completions_select_own on public.schedule_completions;
create policy schedule_completions_select_own on public.schedule_completions
for select to authenticated
using (user_id = (select auth.uid()));
drop policy if exists schedule_completions_write_own on public.schedule_completions;
create policy schedule_completions_insert_own on public.schedule_completions
for insert to authenticated
with check (user_id = (select auth.uid()));
create policy schedule_completions_update_own on public.schedule_completions
for update to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));
create policy schedule_completions_delete_own on public.schedule_completions
for delete to authenticated
using (user_id = (select auth.uid()));

drop policy if exists chat_messages_select_own_session on public.chat_messages;
create policy chat_messages_select_own_session on public.chat_messages
for select to authenticated
using (
  exists (
    select 1
    from public.chat_sessions cs
    where cs.id = chat_messages.session_id
      and cs.user_id = (select auth.uid())
      and private.is_project_member(cs.project_id)
  )
);
drop policy if exists chat_messages_write_own_session on public.chat_messages;
create policy chat_messages_insert_own_session on public.chat_messages
for insert to authenticated
with check (
  exists (
    select 1
    from public.chat_sessions cs
    where cs.id = chat_messages.session_id
      and cs.user_id = (select auth.uid())
      and private.is_project_member(cs.project_id)
  )
);
create policy chat_messages_update_own_session on public.chat_messages
for update to authenticated
using (
  exists (
    select 1
    from public.chat_sessions cs
    where cs.id = chat_messages.session_id
      and cs.user_id = (select auth.uid())
      and private.is_project_member(cs.project_id)
  )
)
with check (
  exists (
    select 1
    from public.chat_sessions cs
    where cs.id = chat_messages.session_id
      and cs.user_id = (select auth.uid())
      and private.is_project_member(cs.project_id)
  )
);
create policy chat_messages_delete_own_session on public.chat_messages
for delete to authenticated
using (
  exists (
    select 1
    from public.chat_sessions cs
    where cs.id = chat_messages.session_id
      and cs.user_id = (select auth.uid())
      and private.is_project_member(cs.project_id)
  )
);
