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
- Color + note CRUD.
- Annotation belongs to one user and one immutable document version.

Current limitation: rectangle annotations are implemented; full PDF text-layer selection/highlight still needs final refinement.

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

The current dashboard aggregates actual project/document/chat/quiz/review data. A rebuildable event/snapshot pipeline is planned as the final progress hardening step.

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

## Known remaining release work

- run full E2E on local machine with real Redis/Celery/PDF/Gemini;
- finish PDF text-layer annotation selection;
- implement rebuildable study-events/progress snapshots;
- add multi-user integration tests using two independent accounts;
- run RAG benchmark and record real metrics;
- validate CI build results;
- configure production Supabase Auth settings;
- deploy backend/worker/frontend and run smoke tests.
