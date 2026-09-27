-- Semantic deduplication support for generated questions.
set search_path = public, extensions;

alter table public.questions
  add column if not exists question_embedding vector(384);

create index if not exists questions_embedding_hnsw_idx
  on public.questions using hnsw (question_embedding vector_cosine_ops)
  where question_embedding is not null;
