# RAGTutor — AI Study Assistant

> Upload tài liệu, chat hỏi đáp với trích dẫn nguồn, lộ trình học cá nhân, sinh quiz và tự chấm điểm bài viết tay.

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind CSS |
| Backend | FastAPI + Python 3.13 |
| Database | Supabase Postgres + pgvector (RLS) |
| Storage | Supabase Storage (private buckets) |
| Auth | Supabase Auth + JWT verification in FastAPI |
| AI | LangChain + Gemini Flash + sentence-transformers (multilingual 384-dim) |
| Background jobs | Celery + Redis |

## Cấu trúc thư mục

```
RAG-Tutor/
├── backend/              # FastAPI app
│   ├── main.py           # Entry point
│   ├── app/
│   │   ├── api/v1/       # REST endpoints
│   │   ├── core/         # Config, auth, database
│   │   ├── services/     # Business logic (RAG, ingestion, grading)
│   │   ├── repositories/ # Database access layer
│   │   └── workers/      # Celery tasks
│   └── migrations/       # SQL migration files
├── frontend/             # Next.js app
│   └── src/
│       ├── app/          # App Router pages
│       ├── lib/          # API client, Supabase client
│       └── providers/    # React Query, auth providers
├── Plan.md
└── Database_design_plan.md
```

## Bắt đầu nhanh

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # điền thông tin Supabase + Gemini
uvicorn main:app --reload
# → http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local   # điền Supabase URL + anon key
npm install
npm run dev
# → http://localhost:3000
```

## API Endpoints (v1)

| Method | Path | Mô tả |
|---|---|---|
| POST | `/api/v1/auth/signup` | Đăng ký |
| POST | `/api/v1/auth/signin` | Đăng nhập |
| GET | `/api/v1/projects` | Danh sách projects |
| POST | `/api/v1/projects` | Tạo project |
| POST | `/api/v1/projects/{id}/documents` | Upload tài liệu |
| DELETE | `/api/v1/projects/{pid}/documents/{did}` | Xóa vĩnh viễn |
| GET | `/api/v1/document-jobs/{id}` | Trạng thái job |
| POST | `/api/v1/projects/{id}/chat/sessions` | Tạo chat session |
| POST | `/api/v1/projects/{pid}/chat/sessions/{sid}/messages` | Gửi tin nhắn (RAG) |
| POST | `/api/v1/projects/{id}/invitations` | Mời thành viên |
| POST | `/api/v1/invitations/{token}/accept` | Chấp nhận lời mời |

> Xem toàn bộ tại `http://localhost:8000/docs`

## Lưu ý free-tier

- Supabase project **tạm dừng sau 7 ngày** không hoạt động — kích hoạt lại trong dashboard.
- Render backend free tier có **cold start** ~30s khi không có traffic.
- Gemini API rate limit thay đổi — kiểm tra [Google AI Studio](https://aistudio.google.com) trước khi deploy.
