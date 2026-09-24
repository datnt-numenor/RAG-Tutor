-- Remove legacy test objects and move RLS helpers out of the exposed public schema.

create schema if not exists private;

alter function public.is_project_member(uuid) set schema private;
alter function public.is_project_owner(uuid) set schema private;

revoke all on function private.is_project_member(uuid) from public, anon;
revoke all on function private.is_project_owner(uuid) from public, anon;
grant usage on schema private to authenticated;
grant execute on function private.is_project_member(uuid) to authenticated;
grant execute on function private.is_project_owner(uuid) to authenticated;

drop function if exists public.match_rag_chunks(vector, integer, double precision);
drop function if exists public.match_rag_chunks(vector, integer);
drop function if exists public.match_rag_chunks(vector);
drop table if exists public.rag_chunks_test cascade;
drop table if exists public.vector_test cascade;
