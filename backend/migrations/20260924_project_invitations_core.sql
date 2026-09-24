-- Project invitation core with token hashing and transactional accept.

create table if not exists public.project_invitations (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  invited_by uuid not null references public.users(id) on delete cascade,
  invited_email varchar(255) not null,
  token_hash text not null unique,
  status text not null default 'pending'
    check (status in ('pending','accepted','rejected','revoked','expired')),
  expires_at timestamptz not null default (now() + interval '7 days'),
  accepted_at timestamptz,
  created_at timestamptz not null default now()
);

create unique index if not exists project_invitation_pending_email_idx
  on public.project_invitations(project_id, lower(invited_email))
  where status = 'pending';

create index if not exists project_invitations_project_id_idx
  on public.project_invitations(project_id);

create or replace function public.accept_project_invitation(
  p_raw_token text,
  p_user_id uuid,
  p_email text
)
returns uuid
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_invitation public.project_invitations;
  v_hash text;
begin
  v_hash := encode(digest(p_raw_token, 'sha256'), 'hex');

  select *
  into v_invitation
  from public.project_invitations
  where token_hash = v_hash
  for update;

  if not found then
    raise exception 'Invitation not found';
  end if;

  if v_invitation.status <> 'pending' then
    raise exception 'Invitation is not pending';
  end if;

  if v_invitation.expires_at <= now() then
    update public.project_invitations
    set status = 'expired'
    where id = v_invitation.id;
    raise exception 'Invitation expired';
  end if;

  if lower(v_invitation.invited_email) <> lower(p_email) then
    raise exception 'Invitation email does not match current user';
  end if;

  insert into public.project_members(project_id, user_id, role)
  values (v_invitation.project_id, p_user_id, 'member')
  on conflict (project_id, user_id) do nothing;

  update public.project_invitations
  set status = 'accepted',
      accepted_at = now()
  where id = v_invitation.id;

  return v_invitation.project_id;
end;
$$;

revoke all on function public.accept_project_invitation(text, uuid, text)
  from public, anon, authenticated;
grant execute on function public.accept_project_invitation(text, uuid, text)
  to service_role;

alter table public.project_invitations enable row level security;
