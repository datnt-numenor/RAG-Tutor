# RAGTutor — AI Study Assistant

RAGTutor là AI Study Assistant multi-user: người dùng tạo project, upload PDF/DOCX, hỏi đáp bằng RAG có citation, đọc/annotate PDF, tạo roadmap học, làm quiz, chấm tự luận và nộp bài bằng ảnh scan.

> Trạng thái hiện tại: phần lớn MVP đã được implement trong code và schema production. Vẫn cần chạy full local E2E + CI/deployment validation trước khi coi là release ổn định.

## Kiến trúc

```text
Next.js App Router
        │
        │ REST / multipart + Supabase JWT
        ▼
FastAPI
 ├─ Supabase Auth/JWKS authorization
 ├─ RAG / Gemini
 ├─ Quiz / OCR / Roadmap
 ├─ Supabase Postgres + pgvector
 ├─ Supabase private Storage
 └─ Redis + Celery workers
```

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4, TanStack Query |
| Backend | FastAPI, Python 3.12+ |
| Auth | Supabase Auth, ES256/RS256 JWT verification via JWKS |
| Database | Supabase PostgreSQL |
| Vector search | pgvector 384-dim, cosine similarity, HNSW |
| Storage | Supabase private buckets |
| Embedding | sentence-transformers `paraphrase-multilingual-MiniLM-L12-v2` |
| LLM / Vision | Gemini model configured by `GEMINI_MODEL` |
| Jobs | Celery + Redis |
| PDF | pdfplumber ingest + pdfjs-dist viewer |
| ORM schema | Prisma Client Python schema retained for relational model documentation/tooling |

## Implemented MVP flows

### Auth & project isolation

- Supabase email/password authentication.
- FastAPI verifies Supabase JWT through JWKS.
- Project owner/member roles.
- Production RLS policies protect direct Supabase access as well as FastAPI authorization.
- Invitation tokens are stored only as SHA-256 hashes and accepted transactionally.
- Private RLS helper functions are not exposed through public RPC.

### Documents & retrieval

```text
Upload PDF/DOCX
→ private Storage
→ document/version/job
→ Celery
→ extract
→ Vietnamese-aware token chunking
→ batch embedding
→ pgvector
→ active version
```

The custom chunker:

- detects headings/paragraphs;
- protects common Vietnamese abbreviations and decimal boundaries;
- splits sentence → clause → word fallback;
- counts tokens with the actual embedding tokenizer;
- never intentionally exceeds model sequence length;
- adds sentence overlap;
- stores page, section, token count and source spans.

Document versions are immutable. Uploading a new version creates a new ingest job and supersedes the old active version only after the new one becomes ready.

Permanent delete immediately removes the document from retrieval, then asynchronously:

- cancels ingest jobs;
- removes Storage objects;
- deletes vectors/chunks;
- marks historical chat citations as `source_deleted`;
- retires questions that no longer have sources;
- removes orphaned active roadmap topics;
- preserves chat and quiz attempt snapshots.

### RAG chat

- Project-scoped multi-document retrieval.
- `match_chunks` filters active document/version at SQL level.
- Similarity threshold + top-k.
- Gemini only runs if retrieval has evidence.
- Otherwise returns `insufficient_evidence`.
- Assistant messages persist model, prompt version, retrieval parameters and citations.
- Redis-backed user quotas protect AI endpoints.
- Request IDs and privacy-safe structured request logs are enabled.

### PDF viewer & annotations

- Signed URL to private document version.
- PDF.js viewer with page navigation and zoom.
- Rectangle highlight coordinates normalized to `0..1`.
- PDF.js text layer supports direct text selection/highlight.
- Text selection is stored as one or more normalized rectangles, so highlight placement survives zoom/resize.
- Color + note CRUD.
- Annotation belongs to one user and one immutable document version.

### Roadmap & schedules

- Gemini extracts topics from active chunks.
- Topic source chunks and prerequisite graph are stored.
- Topological prerequisite ordering.
- Target score, exam date and study minutes/week affect schedule depth and duration.
- Schedule is generated in the user's configured timezone and stored in UTC.
- Suggested/accepted/rejected schedule states.
- Completion is stored separately for each user.

### Quiz & spaced review

Owner can generate the shared question bank; members start quizzes from that bank.

Question generation:

- MCQ and essay;
- each question must reference real source chunks;
- optional mapping to roadmap topic;
- 384-dim question embedding;
- semantic deduplication against old + newly generated questions;
- model/prompt version persisted.

Grading:

- MCQ: exact rule-based grading;
- essay: Gemini grades against key points/rubric **and source evidence**;
- review state updates after grading.

### Handwritten/image answer flow

```text
JPEG / PNG / WebP
→ magic-byte validation
→ private Storage
→ Gemini Vision OCR
→ raw OCR + uncertain regions
→ user edits/confirms
→ essay grading
```

The system never grades OCR text before user confirmation. The image can later be deleted while keeping confirmed text and grading history.

### Progress

- Dashboard aggregates actual project/document/chat/quiz/review data.
- `study_events` stores idempotent activity events.
- `progress_snapshots` stores rebuildable daily aggregates per user/project.
- Schedule completion and graded quiz attempts feed the progress pipeline.
- Snapshot history can be rebuilt for a date range instead of trusting mutable counters.

## Security state

Supabase Security Advisor currently has no table/RLS/pgvector exposure warning. The remaining account-level warning is **Leaked Password Protection Disabled**.

For local development, email confirmation was deliberately disabled earlier. Before public deployment:

1. enable email confirmation;
2. enable leaked-password protection if available on the chosen Supabase plan;
3. rerun authorization integration tests.

## Project structure

```text
RAG-Tutor/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/
│   │   ├── core/
│   │   ├── services/
│   │   └── workers/
│   ├── evaluation/
│   ├── migrations/
│   ├── prisma/
│   ├── tests/
│   ├── Dockerfile
│   └── main.py
├── frontend/
│   ├── src/app/
│   ├── src/components/
│   ├── src/lib/
│   ├── src/providers/
│   └── Dockerfile
├── .github/workflows/ci.yml
├── docker-compose.yml
├── render.yaml
├── Plan.md
└── Database_design_plan.md
```

## Local development

### 1. Environment

Backend:

```powershell
cd "D:\Personal Project\RAGTutor\backend"
..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy:

```text
backend/.env.example → backend/.env
frontend/.env.example → frontend/.env.local
```

Never commit service-role keys, database passwords or Gemini keys.

### 2. Redis

With Docker:

```powershell
docker run --name ragtutor-redis -p 6379:6379 -d redis:7-alpine
```

### 3. Celery

Windows local:

```powershell
cd backend
celery -A app.workers.celery_app.celery_app worker --loglevel=info --pool=solo
```

### 4. Backend

```powershell
cd backend
uvicorn main:app --reload
```

Development Swagger:

```text
http://127.0.0.1:8000/docs
```

### 5. Frontend

```powershell
cd frontend
npm ci
npm run dev
```

Open:

```text
http://localhost:3000
```

## Docker Compose

After filling `backend/.env` and exporting frontend public Supabase variables:

```bash
docker compose up --build
```

Services:

- frontend: 3000
- API: 8000
- Redis: 6379
- Celery worker

## Tests

Backend core tests:

```bash
cd backend
pytest -q
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

GitHub Actions CI is defined in `.github/workflows/ci.yml`.

## End-to-end smoke test

Sau khi Redis, Celery worker và FastAPI đang chạy, có thể kiểm tra toàn bộ vertical slice bằng một lệnh. Script tự tạo một DOCX tạm chứa kiến thức Transformer, upload, chờ ingest và hỏi một câu RAG có citation.

PowerShell:

```powershell
cd backend
$env:RAGTUTOR_TEST_EMAIL="your-test-account@example.com"
$env:RAGTUTOR_TEST_PASSWORD="<local-test-password>"
python scripts/smoke_e2e.py
```

Hoặc truyền tham số trực tiếp:

```bash
python scripts/smoke_e2e.py \
  --email your-test-account@example.com \
  --password '<password>' \
  --base-url http://127.0.0.1:8000/api/v1 \
  --timeout 180
```

Flow được kiểm tra:

```text
sign in
→ /auth/me
→ create project
→ generate temporary DOCX
→ upload document
→ Celery ingest polling
→ active version = ready
→ create chat session
→ RAG question
→ grounded answer contains Query/Key/Value
→ at least one citation
```

Không commit test password hoặc access token vào repository.

## RAG evaluation

Create a fixed JSONL dataset such as:

```json
{"question":"Attention dùng các vector nào?","expected_document":"transformer.pdf","expected_page":2,"answer_keywords":["query","key","value"],"should_abstain":false}
{"question":"Thông tin hoàn toàn không có trong tài liệu?","should_abstain":true}
```

Run:

```bash
cd backend
python -m evaluation.run_rag_eval \
  --project-id <PROJECT_UUID> \
  --dataset evaluation/my_eval.jsonl \
  --output evaluation/result.json
```

Metrics:

- retrieval hit rate;
- citation hit rate;
- abstain accuracy;
- keyword coverage;
- median retrieval latency;
- median end-to-end latency.

Do not claim CV metrics until they have been measured on a fixed test set.

## Main API groups

```text
/auth
/projects
/documents
/document-jobs
/chat
/quiz
/annotations
/roadmap
/schedules
/progress
/invitations
```

Full API reference is available through Swagger in non-production mode.

## Deploy

- `render.yaml` provisions the FastAPI web service and Celery worker blueprint.
- `frontend/vercel.json` contains the Vercel Next.js build configuration.
- Redis remains an external deployment dependency and is supplied through `REDIS_URL`.
- Production secrets are configured in the hosting provider, never committed to Git.

## Known remaining release work

- run full E2E on a real local/deployed environment with Redis/Celery/PDF/Gemini;
- add multi-user authorization integration tests using two independent accounts;
- run the fixed RAG benchmark and record real metrics;
- verify GitHub Actions after the latest frontend/backend changes;
- enable production Supabase Auth email confirmation and leaked-password protection where available;
- deploy API/worker/frontend and run post-deploy smoke tests.
