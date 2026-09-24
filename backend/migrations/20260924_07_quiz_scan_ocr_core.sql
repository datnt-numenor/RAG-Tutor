-- Scan/OCR support for essay attempts.

alter table public.quiz_attempts
  add column if not exists submission_type text not null default 'text',
  add column if not exists rubric_snapshot jsonb,
  add column if not exists ocr_raw_text text,
  add column if not exists ocr_confirmed_text text,
  add column if not exists ocr_uncertain_regions jsonb,
  add column if not exists image_storage_path text,
  add column if not exists image_deleted_at timestamptz;

alter table public.quiz_attempts
  drop constraint if exists quiz_attempts_submission_type_check;

alter table public.quiz_attempts
  add constraint quiz_attempts_submission_type_check
  check (submission_type in ('text','image_scan'));

alter table public.quiz_attempts
  drop constraint if exists quiz_attempts_status_check;

alter table public.quiz_attempts
  add constraint quiz_attempts_status_check
  check (status in ('draft','ocr_pending_confirmation','submitted','graded','error'));

insert into storage.buckets (id, name, public)
values ('quiz-submissions', 'quiz-submissions', false)
on conflict (id) do update set public = false;
