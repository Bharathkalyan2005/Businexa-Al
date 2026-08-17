# BizLens AI — Deployment Guide

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│  User Browser                                         │
│        │                                              │
│        ▼                                              │
│  Vercel (Next.js)  ◄─── Clerk (Auth)                 │
│        │                                              │
│        ├── Neon Postgres (Drizzle ORM)                │
│        ├── Vercel Blob (file storage)                 │
│        │                                              │
│        └── Render/Railway (FastAPI Python Service)    │
│                 │                                     │
│                 ├── Neon Postgres                     │
│                 ├── Vercel Blob (PDF upload)          │
│                 └── Google Gemini API (AI)            │
└──────────────────────────────────────────────────────┘
```

---

## Step 1 — Set Up External Services (Before Deploying)

### 1a. Clerk (Authentication)
1. Go to [clerk.com](https://clerk.com) → Create a new application
2. Choose **Email + Password** (or add Google OAuth)
3. Copy your **Publishable Key** and **Secret Key** from the Clerk dashboard
4. In the Clerk dashboard → Redirects, set:
   - Sign-in URL: `/sign-in`
   - Sign-up URL: `/sign-up`
   - After sign-in: `/dashboard`
   - After sign-up: `/create-business`

### 1b. Neon Postgres (Database)
1. Go to [neon.tech](https://neon.tech) → Create project
2. Copy the **pooled connection string** (use the pooler URL, not the direct URL)
   - It looks like: `postgresql://user:pass@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require`
3. Keep this for both the web and api services

### 1c. Vercel Blob (File Storage)
1. Go to your [Vercel dashboard](https://vercel.com) → Storage → Create Blob store
2. Copy the **Read/Write Token** — you'll need it in both services

### 1d. Google Gemini API Key
1. Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Keep it for the Python service only

---

## Step 2 — Run Database Migration

```bash
cd web
cp .env.example .env.local
# Fill in DATABASE_URL and CLERK keys
npx drizzle-kit push
```

Verify the tables exist by checking your Neon console — you should see:
`users`, `businesses`, `datasets`, `dataset_columns`, `metrics_snapshots`, `insights`, `chat_messages`, `reports`

---

## Step 3 — Deploy Python API to Render

1. Push the repo to GitHub
2. Go to [render.com](https://render.com) → New → **Web Service**
3. Connect your GitHub repo → Select the `api/` directory as root
4. Configure:
   - **Runtime**: Docker
   - **Dockerfile path**: `./Dockerfile`
   - **Instance type**: Starter (512MB RAM is enough for Pandas)
5. Add these **Environment Variables** in the Render dashboard:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Your Neon pooled connection string |
| `INTERNAL_API_KEY` | A strong random secret (generate with `openssl rand -hex 32`) |
| `CORS_ORIGINS` | `https://your-app.vercel.app` (fill in after step 4) |
| `GEMINI_API_KEY` | Your Gemini API key |
| `BLOB_READ_WRITE_TOKEN` | Your Vercel Blob token |
| `RATE_LIMIT_CHAT` | `10` |
| `RATE_LIMIT_REPORTS` | `5` |

6. Deploy — wait for the health check at `/health` to return `{"status":"ok"}`
7. Copy the Render service URL (e.g. `https://bizlens-api.onrender.com`)

---

## Step 4 — Deploy Next.js Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) → Import Git Repository
2. Set **Root Directory** to `web`
3. Add these **Environment Variables** in Vercel:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Your Neon pooled connection string |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | From Clerk dashboard |
| `CLERK_SECRET_KEY` | From Clerk dashboard |
| `NEXT_PUBLIC_CLERK_SIGN_IN_URL` | `/sign-in` |
| `NEXT_PUBLIC_CLERK_SIGN_UP_URL` | `/sign-up` |
| `BLOB_READ_WRITE_TOKEN` | Your Vercel Blob token |
| `PYTHON_API_URL` | Your Render service URL from Step 3 |
| `INTERNAL_API_KEY` | Same secret as in Render |

4. Deploy. Copy the Vercel production URL.

---

## Step 5 — Post-Deploy Config

1. **Update Render CORS**: Go back to Render → Edit env → Set `CORS_ORIGINS` to your Vercel URL
2. **Update Clerk redirect URLs**: Add your Vercel domain in Clerk dashboard → Domains

---

## Pre-Launch Checklist

### Environment Variables
- [ ] `DATABASE_URL` set in both Vercel and Render (pooled string)
- [ ] `CLERK_SECRET_KEY` set in Vercel (never expose client-side)
- [ ] `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` set in Vercel
- [ ] `BLOB_READ_WRITE_TOKEN` set in both Vercel and Render
- [ ] `INTERNAL_API_KEY` is the **same value** in both services
- [ ] `PYTHON_API_URL` in Vercel points to Render URL (https://)
- [ ] `CORS_ORIGINS` in Render is exactly your Vercel domain

### Security
- [ ] No secrets in git history (`git log --all -- .env` returns nothing sensitive)
- [ ] `.env` and `.env.local` are in `.gitignore`
- [ ] Render service returns 401 when calling `/ai/chat` without `X-Internal-Key`
- [ ] CORS rejects request from `https://evil.com` (test with curl)

### Functional E2E Test (do this on the deployed URLs)
1. [ ] Sign up with a new email → lands on Create Business
2. [ ] Create business (e.g. "Test Restaurant", type: Restaurant)
3. [ ] Upload `sample_restaurant_sales.xlsx` → see profiling results
4. [ ] Navigate to Dashboard → see KPI cards populated with real data
5. [ ] Ask a question in the AI chat → get a real Gemini response
6. [ ] Go to Reports → click Generate New Report → PDF downloads
7. [ ] Sign out → sign back in → data is still there

---

## Running Locally

```bash
# Terminal 1 — Python API
cd api
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — Next.js
cd web
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

> **Note**: Without real Clerk keys, auth will be mocked/broken. You can use the placeholder keys for UI development only — sign-in/sign-up won't work.

---

## Rollback Plan

| Scenario | Action |
|----------|--------|
| Python API broken after deploy | Render → Deploys → click **Rollback** to previous deploy |
| Frontend broken after deploy | Vercel → Deployments → click **Promote** on the last working deployment |
| DB migration failed | Neon → Branches → restore from the automatic backup before migration |
| LLM costs spiking | Set `RATE_LIMIT_CHAT=1` in Render env → will restart automatically |

---

## Cost Estimates (monthly, at light usage)

| Service | Free Tier | Paid |
|---------|-----------|------|
| Neon Postgres | 0.5 GB / 191 compute hours | ~$19/mo for more |
| Vercel (frontend) | Hobby plan free | $20/mo Pro |
| Render (Python API) | 750 hrs free | $7/mo Starter |
| Vercel Blob | 1 GB free | $0.023/GB |
| Gemini API | Free tier generous | ~$0.075/1M tokens |

**Total to get started: $0 (all free tiers)**
