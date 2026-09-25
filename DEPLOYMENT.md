# Production Deployment

RAGTutor is code-complete enough for release validation. Production deployment is intentionally split into two phases so no service is launched with missing secrets.

## Current infrastructure

- Supabase production project: configured.
- Railway project: `RAGTutor`.
- Railway Redis: provisioned and healthy.
- Railway API service: created and preconfigured, source not attached yet.
- Railway Celery worker: created and preconfigured, source not attached yet.
- Frontend production is running on Railway. Vercel remains an optional migration target.

## Private secrets still required

Do not commit these values to Git.

GitHub Actions repository secrets:

- `SUPABASE_SERVICE_KEY`
- `GEMINI_API_KEY`

Railway production environment also needs the same two private values:

- `SUPABASE_SERVICE_KEY`
- `GEMINI_API_KEY`

Optional primary AI providers (recommended to reduce Gemini free-tier pressure):

- `GROQ_API_KEY`: enables Groq for text generation, streaming, and vision.
- `GROQ_MODEL=qwen/qwen3.8-27b`
- `GROQ_VISION_MODEL=qwen/qwen3.8-27b`
- `AZURE_VISION_ENDPOINT`: enables Azure Image Analysis OCR before LLM vision.
- `AZURE_VISION_KEY`

Routing is `Groq -> Gemini` for text and `Azure Vision -> Groq Vision -> Gemini`
for OCR. Missing optional credentials are skipped automatically.

Public values are already known/configured where appropriate:

- `SUPABASE_URL=https://xlreazpjvcudvbslrzdw.supabase.co`
- Supabase publishable key
- `GEMINI_MODEL=gemini-3.6-flash`
- `EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2`
- `EMBEDDING_DIM=384`
- Railway private Redis URL

## Runtime validation

Workflow: `.github/workflows/runtime-e2e.yml`

It performs:

1. Start Redis.
2. Install the backend.
3. Create two temporary Supabase Auth users.
4. Start FastAPI and Celery.
5. Upload a DOCX.
6. Wait for ingestion.
7. Verify RAG answer and citations.
8. Run a fixed retrieval/abstention evaluation.
9. Run cross-user authorization tests.
10. Delete temporary projects/users even when the run fails.

The first real run reached the secret-validation gate and stopped because the two private repository secrets were not configured. No application runtime error was reached.

## Railway services

API configuration:

- Root: `/backend`
- Dockerfile: `Dockerfile`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health/ready`

Worker configuration:

- Root: `/backend`
- Dockerfile: `Dockerfile`
- Start: `celery -A app.workers.celery_app.celery_app worker --loglevel=info --concurrency=1`

After the private values are set:

1. Attach `datnt-numenor/RAG-Tutor` main branch as the source for both Railway services.
2. Deploy API and worker.
3. Generate a public Railway domain for the API.
4. Set `ALLOWED_ORIGINS` to the final Vercel origin.
5. Deploy frontend with:
   - `NEXT_PUBLIC_API_BASE_URL=https://<api-domain>/api/v1`
   - `NEXT_PUBLIC_SUPABASE_URL=https://xlreazpjvcudvbslrzdw.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY=<publishable-key>`
6. Run post-deploy smoke tests.


## Current live URLs

- Web: `https://rag-tutor-web-production.up.railway.app`
- API: `https://rag-tutor-api-production.up.railway.app`

The web service is built from `/frontend/Dockerfile`. The API uses `/health/ready` so Railway only marks it healthy when both Supabase and Redis are reachable.
