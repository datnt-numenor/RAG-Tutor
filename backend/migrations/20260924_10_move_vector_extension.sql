-- Move pgvector out of public while keeping match_chunks operator resolution intact.

alter function public.match_chunks(uuid, vector, integer, double precision)
  set search_path = public, extensions;

alter extension vector set schema extensions;
