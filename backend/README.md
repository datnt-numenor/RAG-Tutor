# RAGTutor Backend

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt

# Copy and fill env vars
cp .env.example .env

# Generate Prisma client
prisma generate --schema=prisma/schema.prisma

# Run dev server
uvicorn main:app --reload
# → http://localhost:8000/docs
```

## Prisma commands

```bash
# Generate client after schema changes
prisma generate --schema=prisma/schema.prisma

# Push schema to DB (dev only — use migrations in production)
prisma db push --schema=prisma/schema.prisma

# Open Prisma Studio
prisma studio --schema=prisma/schema.prisma
```

> **Note:** `embedding` (VECTOR 384) and `question_embedding` columns are **not** in Prisma schema.  
> They are managed via raw SQL migrations and queried through Supabase RPC `match_chunks`.

## Folder structure

```
backend/
├── prisma/
│   └── schema.prisma        # 23 tables
├── app/
│   ├── api/v1/endpoints/    # Route handlers
│   ├── core/                # Config, auth, Prisma client
│   ├── schemas/             # Pydantic I/O models
│   ├── services/            # Business logic
│   ├── repositories/        # Prisma query layer
│   └── workers/             # Celery tasks
├── migrations/              # Versioned SQL (pgvector, RLS, triggers)
└── tests/
```
