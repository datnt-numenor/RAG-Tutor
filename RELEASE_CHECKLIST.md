# RAGTutor Release Validation

This file tracks release gates that require a real runtime rather than code inspection alone.

## Automated in CI

- [x] Backend Python sources compile.
- [x] Core backend unit tests pass.
- [x] Frontend lint passes.
- [x] Next.js production build succeeds.
- [x] Frontend dependency audit has no high/critical vulnerability.
- [x] Backend CI/Render dependency set uses CPU-only PyTorch instead of CUDA runtimes.

CI verified on `main` through GitHub Actions run #158 and subsequent release-hardening pushes.

## Verified against Supabase

- [x] Production tables have RLS enabled.
- [x] Security Advisor has no schema/RLS exposure warning.
- [x] RLS smoke test: project owner can read/update their project.
- [x] RLS smoke test: outsider cannot read project or private chat session.
- [x] Temporary RLS smoke data is cleaned up.
- [x] Duplicate permissive RLS policies are removed.
- [ ] Enable leaked-password protection in Supabase Auth before public release.
- [ ] Re-enable email confirmation before public release.

## Runtime E2E

Requires real Redis, Celery, Gemini and app environment variables.

- [ ] Run `backend/scripts/smoke_e2e.py` — Runtime E2E workflow is ready; currently blocked only by missing `SUPABASE_SERVICE_KEY` and `GEMINI_API_KEY` GitHub Actions secrets.
- [ ] Run `backend/scripts/security_e2e.py` with two independent users — workflow now creates/deletes disposable Supabase Auth users automatically.
- [ ] Verify PDF upload, ingest, citation deep-link and permanent deletion.
- [ ] Verify OCR image upload → confirmation → essay grading.
- [ ] Verify roadmap/schedule generation.
- [ ] Run fixed RAG evaluation dataset and record measured metrics.

## Deployment

- [ ] Deploy API on Railway from `datnt-numenor/RAG-Tutor` once private runtime secrets are configured.
- [x] Provision production Redis on Railway (`RAGTutor` project).
- [x] Railway worker connected to private Redis (`redis.railway.internal:6379/0`) and Celery reports ready.
- [x] Railway public API domain created: `https://rag-tutor-api-production.up.railway.app`.
- [x] Railway API and Celery services deployed from `main`; API, worker and Redis are online.
- [x] API readiness healthcheck `/health/ready` passes on Railway, verifying Supabase + Redis connectivity.
- [ ] Frontend deployment: Railway service `rag-tutor-web` is building from `/frontend`; Vercel connector remains optional/follow-up.
- [ ] Configure production CORS and public frontend environment variables.
- [ ] Run post-deploy smoke tests.
- [ ] Record cold-start and RAG latency measurements.

Do not mark RAG accuracy, latency, OCR accuracy, or grading quality as complete until measured on a fixed dataset.
