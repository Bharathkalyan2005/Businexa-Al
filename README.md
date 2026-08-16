# Businexa AI

AI-powered business analytics for small business owners. Upload sales data, get deterministic KPIs, and plain-language insights.

## Monorepo structure

| Folder | Purpose | Deploy target |
|--------|---------|---------------|
| `web/` | Next.js frontend (auth, dashboard, upload UI) | Vercel |
| `api/` | FastAPI analytics service (profiling, cleaning, analytics) | Render / Railway |

## Local development

### Prerequisites

- Node.js 20+
- Python 3.12+
- A [Neon](https://neon.tech) Postgres database
- A [Clerk](https://clerk.com) application
- A [Vercel Blob](https://vercel.com/docs/storage/vercel-blob) store (for file uploads)

### 1. Configure environment variables

```bash
# Frontend
cd web
cp .env.example .env.local
# Fill in: DATABASE_URL, NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY,
#          BLOB_READ_WRITE_TOKEN, PYTHON_API_URL, INTERNAL_API_KEY

# API service
cd ../api
cp .env.example .env
# Fill in: DATABASE_URL, INTERNAL_API_KEY (must match web), CORS_ORIGINS
```

### 2. Install dependencies & run

**Terminal 1 — Next.js frontend:**
```bash
cd web
npm install
npm run db:push    # Push schema to Neon
npm run dev        # http://localhost:3000
```

**Terminal 2 — Python API:**
```bash
cd api
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload  # http://localhost:8000
```

### 3. Run Python tests
```bash
cd api
.venv\Scripts\activate
pytest tests/ -v
```

### Test flow

1. Sign up at `/sign-up`
2. Create your first business at `/create-business`
3. Navigate to Upload → drop a CSV file
4. See profiling results (columns, types, quality score)
5. Check the dashboard for data status

## Build phases

- **Phase 1** — Auth, DB, navigation shell ✅
- **Phase 2** — File upload + data profiling ✅
- **Phase 3** — Cleaning + analytics engine
- **Phase 4** — Dashboard UI
- **Phase 5** — AI insights + chat
- **Phase 6** — PDF reports
- **Phase 7** — Security review + deployment

