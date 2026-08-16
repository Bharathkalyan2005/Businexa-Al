# Businexa AI — Production Deployment Guide

Businexa AI consists of two services sharing one Neon Postgres database:
1. **Frontend (`web/`)**: Next.js App deployed to **Vercel**.
2. **Backend (`api/`)**: FastAPI Analytics & AI service deployed to **Render** or **Railway**.
3. **Database**: **Neon** serverless Postgres (already configured & migrated).

---

## 1. Database (Neon Postgres)

- **Connection URL**: Ensure you use the pooled connection string (`?sslmode=require`)
- **Schema Migrations**:
  To push schema updates to production:
  ```bash
  cd web
  npm run db:push
  ```

---

## 2. Deploy Python API (`api/`) to Render / Railway

### Option A: Render (Web Service)
1. In Render Dashboard, click **New > Web Service**.
2. Connect your Git repository and set Root Directory to `api`.
3. Select **Docker** as the runtime (or Python 3.12+).
4. Configure Environment Variables:
   - `DATABASE_URL`: `postgresql://neondb_owner:...@...neon.tech/neondb?sslmode=require`
   - `INTERNAL_API_KEY`: A strong random string (e.g. 32-char hex).
   - `GEMINI_API_KEY`: Your Google Gemini API key.
   - `CORS_ORIGINS`: `https://your-frontend.vercel.app`
5. Port: `8000`.

### Option B: Railway
1. Click **New Project > Deploy from GitHub repo**.
2. Set Root Directory to `/api`.
3. Add the same Environment Variables listed above.

---

## 3. Deploy Frontend (`web/`) to Vercel

1. In Vercel Dashboard, click **Add New > Project**.
2. Select your repository and choose `web` as the Root Directory.
3. Configure Environment Variables:
   - `DATABASE_URL`: Your Neon pooled connection string.
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`: From Clerk dashboard.
   - `CLERK_SECRET_KEY`: From Clerk dashboard.
   - `NEXT_PUBLIC_CLERK_SIGN_IN_URL`: `/sign-in`
   - `NEXT_PUBLIC_CLERK_SIGN_UP_URL`: `/sign-up`
   - `PYTHON_API_URL`: Your deployed Python service URL (e.g. `https://bizlens-api.onrender.com`).
   - `INTERNAL_API_KEY`: Must match the Python service `INTERNAL_API_KEY`.
   - `BLOB_READ_WRITE_TOKEN`: (Optional) From Vercel Blob store if using cloud blob storage.
4. Click **Deploy**.

---

## 4. Pre-Launch Security & Verification Checklist

- [ ] All database queries scoped to `user_id` / `business_id` (multi-tenant isolated).
- [ ] Next.js sends `X-Internal-Api-Key` on every request to FastAPI.
- [ ] FastAPI rejects unauthenticated requests with 401 Unauthorized.
- [ ] Large CSV / Excel file guard (10 MB limit & 100k row ceiling).
- [ ] Non-negotiable architectural rule verified: LLM only receives structured precomputed metrics JSON; never raw CSV rows or unchecked mathematical operations.
- [ ] Security headers enabled in `next.config.ts`.
