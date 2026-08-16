# BizLens AI — Complete Phase-by-Phase Build Prompts

Paste one phase into Claude Code/Cursor at a time. Wait for it to finish and test before moving to the next. Replace every `<...>` placeholder with your own values — never paste real secrets into the chat itself; tell the agent to read them from `.env`.

---

## PHASE 0 — Planning Only (no code)

```
You are a senior full-stack engineer, AI engineer, data analyst, and product architect.

I am building "BizLens AI" — a SaaS platform where small business owners upload
CSV/Excel sales data and the platform automatically cleans it, calculates real
KPIs (revenue, profit, growth, top products, customer trends), detects anomalies,
and explains the results in plain language via a dashboard and an AI chat interface.

CORE ARCHITECTURAL RULE (non-negotiable): The LLM never performs calculations.
A Python/Pandas analytics engine computes every metric deterministically first.
The LLM only explains verified structured JSON output that Python hands it.

TECH STACK:
- Frontend: Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui
- Charts: Recharts
- Auth: Clerk (or Auth.js if you recommend it instead — tell me your reasoning)
- Database: Neon (serverless Postgres), accessed via Drizzle ORM
- File storage: Vercel Blob
- Analytics backend: separate Python service (FastAPI + Pandas + NumPy)
- AI: Anthropic Claude API, used only for explanation/chat, never computation
- Hosting: Vercel (frontend), Render or Railway (Python service), Neon (DB)

MVP SCOPE (build only this first):
Login -> Create business -> Upload CSV/Excel -> Data profiling -> Data cleaning
-> Automatic KPI analysis -> Dashboard -> AI insights -> Ask-AI chat -> PDF report

OUT OF SCOPE for v1: third-party integrations (Shopify, Stripe, Google Sheets),
multi-business-type auto-detection, billing, team accounts.

DATA MODEL (Postgres):
users (id, email, name, created_at)
businesses (id, user_id, name, business_type, created_at)
datasets (id, business_id, filename, storage_url, status, uploaded_at)
dataset_columns (id, dataset_id, column_name, detected_type)
metrics_snapshots (id, dataset_id, revenue, profit, orders, growth_pct, top_product, computed_at, raw_json)
insights (id, dataset_id, insight_text, category, created_at)
chat_messages (id, business_id, role, content, created_at)
reports (id, business_id, dataset_id, pdf_url, generated_at)

DO NOT WRITE ANY CODE YET.

Instead:
1. Propose the exact monorepo/folder structure for both the Next.js app and the
   Python service (I want them as two deployable projects, possibly in one repo
   with separate folders, e.g. /web and /api).
2. Write the Drizzle ORM schema file matching the data model above.
3. Break the build into the 7 phases I'll give you one at a time, and for each
   phase list the specific files you expect to create or modify.
4. Flag any part of this plan you think is wrong or would cause problems at
   scale, and propose a fix.

Wait for my explicit confirmation before writing any implementation code.
```

---

## PHASE 1 — Foundation (Auth + DB + Project Skeleton)

```
Build Phase 1 of BizLens AI. Reference the architecture and data model we agreed
on in the planning step.

SCOPE FOR THIS PHASE ONLY:
1. Initialize the Next.js (App Router, TypeScript) project with Tailwind CSS
   and shadcn/ui installed and configured.
2. Set up Clerk authentication with sign-up, sign-in, and a protected route
   group for everything under /dashboard.
3. Connect to Neon Postgres using Drizzle ORM. Create the schema exactly as
   specified (users, businesses, datasets, dataset_columns, metrics_snapshots,
   insights, chat_messages, reports). Generate and run the initial migration.
4. Build a minimal "Create Business" flow: after sign-up, the user lands on a
   page to create their first business (name + business_type dropdown:
   Retail / Restaurant / Salon / Cleaning Service / E-commerce / Other).
5. Build a basic authenticated layout with a sidebar: Dashboard, Upload,
   Reports, Settings (pages can be empty placeholders for now except Dashboard
   which should show "No data yet — upload a file to get started").

DO NOT implement file upload, analytics, or AI features yet — those are later
phases. Keep this phase strictly to auth + database + navigation shell.

REQUIREMENTS:
- All secrets (DATABASE_URL, CLERK keys) must be read from environment
  variables via a `.env.local` file. Add `.env.local` to `.gitignore`.
  Create a `.env.example` file listing the required variable names with
  placeholder values, no real secrets.
- A user must only ever see their own businesses — enforce this in every
  query, not just in the UI.
- Use TypeScript strictly; no `any` types.
- After building, tell me exactly which npm packages you installed and the
  exact `.env.local` variables I need to fill in myself.

When done, give me the commands to run it locally so I can test sign-up,
business creation, and navigation before we move to Phase 2.
```

---

## PHASE 2 — File Upload + Data Profiling

```
Build Phase 2 of BizLens AI. Phase 1 (auth, DB, navigation shell) is complete
and working.

SCOPE FOR THIS PHASE:

Frontend (Next.js):
1. Build an "Upload" page under /dashboard/upload that accepts .csv and .xlsx
   files via drag-and-drop or file picker (max 10MB, validate file type
   client-side and server-side).
2. On upload, store the raw file in Vercel Blob and create a `datasets` row
   with status = "uploaded".
3. Show a processing state while profiling runs, then display the profiling
   results: detected columns, detected data types, missing value counts per
   column, and a computed "Data Quality Score" out of 100.

Backend (new Python service, separate from the Next.js app):
1. Scaffold a FastAPI project in a new /api folder (or wherever we agreed in
   planning) with a clear structure: routers, services, models.
2. Implement `POST /datasets/upload` — accepts a file reference (blob URL) and
   dataset_id, downloads the file, parses it with Pandas.
3. Implement `POST /datasets/{id}/profile` — detects column names, infers types
   (date, numeric, categorical, currency), counts missing values and
   duplicate rows, and returns a JSON quality score calculation. Store the
   column-level results in `dataset_columns`.
4. Handle malformed files gracefully (wrong format, empty file, unreadable
   encoding) and return clear error messages the frontend can display.
5. Write unit tests for the profiling logic using at least 3 sample CSVs you
   generate yourself (clean data, data with missing values, data with wrong
   types) — put these fixtures in a /tests/fixtures folder.

CONNECT THE TWO SERVICES:
- The Next.js app calls the Python API over HTTP. Define the base URL as an
  environment variable (PYTHON_API_URL) so it works both locally and once
  deployed separately.
- Do NOT proxy raw file bytes through Next.js if avoidable — prefer having
  Python fetch directly from the Blob URL.

Do not implement cleaning, analytics/KPI calculation, or AI features yet.

When done, tell me how to run both services locally together, and give me a
sample CSV I can use to manually test the full upload -> profile flow.
```

---

## PHASE 3 — Data Cleaning + Analytics Engine

```
Build Phase 3 of BizLens AI. Upload and profiling (Phase 2) work end-to-end.

SCOPE FOR THIS PHASE (Python service only, plus minimal frontend wiring):

1. Implement `POST /datasets/{id}/clean`:
   - Remove exact duplicate rows, log how many were removed.
   - Handle missing values per column type (numeric -> flag for review or
     impute per a documented rule; date -> flag invalid dates; categorical ->
     leave as "Unknown" rather than silently dropping rows).
   - Normalize currency/number formatting (strip symbols, commas) into clean
     numeric columns.
   - Return a cleaning summary: rows removed, values imputed, remaining issues.

2. Implement `POST /datasets/{id}/analyze`:
   - Calculate: total revenue, total orders, average order value, total
     profit (if cost data exists), profit margin, revenue growth % vs prior
     period, top 3 products by revenue, bottom 3 products by revenue,
     revenue by day/week/month, customer count and repeat-customer rate if a
     customer column exists.
   - Adapt which metrics are calculated based on `business_type` on the
     business record (e.g. Retail gets inventory/stock-turnover style
     metrics if columns support it; Restaurant gets food-cost style metrics).
     If required columns for a metric don't exist, skip that metric rather
     than guessing.
   - Implement the deterministic insight rules, for example:
     - if revenue_growth > 10: "Revenue is growing strongly."
     - if profit_growth < revenue_growth: "Profit is growing slower than
       revenue — costs may be rising faster than sales."
     - if any single product's sales changed by more than -20%: flag it.
     - if any day's revenue is less than 50% of the trailing 7-day average:
       flag as an anomaly.
   - Store the full computed result in `metrics_snapshots.raw_json` and the
     individual insight strings in the `insights` table with a category
     (growth / profitability / anomaly / product).

3. WRITE UNIT TESTS for every single calculation above using deterministic
   fixture data where you know the correct answer in advance (e.g. a CSV
   where you've hand-calculated total revenue = exactly X). Do not skip this
   — these numbers are the entire credibility of the product.

4. Minimal frontend wiring: after profiling completes, automatically trigger
   clean -> analyze, and show a simple JSON/table view of the resulting
   metrics on the dashboard page (final polished dashboard UI comes in
   Phase 4 — for now just prove the numbers are correct and visible).

Do not implement charts, AI insights, or chat yet.

When done, show me the test results and tell me how to inspect the raw
computed metrics for a sample dataset so I can manually verify the numbers.
```

---

## PHASE 4 — Dashboard UI

```
Build Phase 4 of BizLens AI. The analytics engine (Phase 3) produces correct,
tested metrics that are currently shown as raw JSON/tables.

SCOPE FOR THIS PHASE (frontend only, using real data — no mock data anywhere):

1. Build the main dashboard at /dashboard/[businessId] with this layout:
   - Header: "Good morning, {name} — here's what's happening in your business."
   - KPI cards row: Revenue, Profit, Orders, Average Order Value (each with
     the value and the growth % vs prior period, colored green/red).
   - Revenue Trend chart (line chart, Recharts) — daily or monthly depending
     on data range.
   - Profit Trend chart.
   - Top Products table/list (top 3 by revenue, with revenue and % of total).
   - Customer Performance section (only render if customer data exists in
     this dataset — do not show empty/fake sections).
   - "AI Insights" cards section — for now, just render the deterministic
     insight strings from the `insights` table as plain cards (LLM rewriting
     comes in Phase 5).
   - "Business Health Score" — a single composite indicator derived from the
     metrics we already computed (define the formula explicitly and show me
     what you chose).

2. States to handle properly:
   - Loading state: skeleton loaders matching the final layout, not spinners.
   - Empty state: no dataset uploaded yet -> prompt to upload.
   - Error state: analysis failed -> show what went wrong, offer retry.

3. Design direction: modern, minimal, professional B2B SaaS look. Use cards,
   subtle borders/shadows, clear typography hierarchy. Avoid heavy gradients,
   glow effects, or generic "AI product" visual clichés. Follow shadcn/ui
   conventions consistently.

4. Make it responsive — usable on mobile, not just desktop.

Do not implement the AI chat or PDF report generation yet.

When done, tell me which dataset/business I should test with to see a fully
populated dashboard, and flag anywhere you had to make an assumption because
the underlying data didn't support a section cleanly.
```

---

## PHASE 5 — AI Insights + Ask-Your-Data Chat

```
Build Phase 5 of BizLens AI. The dashboard (Phase 4) renders real, correct
metrics and raw deterministic insight strings.

SCOPE FOR THIS PHASE:

1. Integrate the Anthropic Claude API (Python service side, not the frontend
   directly — keep the API key server-side only).

2. Implement `GET /insights/{business_id}`:
   - Take the deterministic insight strings + the structured metrics JSON
     already computed in Phase 3.
   - Send ONLY this structured summary to Claude (never raw transaction-level
     data) with a system prompt instructing it to explain the numbers in
     plain business language and suggest 2-3 concrete next actions, without
     inventing any numbers not present in the input.
   - Store the LLM's response and render it in the "AI Insights" section on
     the dashboard, replacing the raw strings from Phase 4.

3. Implement `POST /ai/chat` — the "Ask your business" feature:
   - Accept a natural-language question from the user (e.g. "Why did profit
     decrease this month?").
   - Do NOT send the raw dataset to the LLM. Instead, pass the relevant
     precomputed metrics/insights (and if the question needs something not
     yet computed, run the appropriate Python calculation first, then hand
     the result to the LLM).
   - Persist the conversation in `chat_messages` scoped to the business.
   - Return the LLM's answer to the frontend.

4. Frontend: build the chat UI on the dashboard — a simple input box
   ("Ask your business anything...") with a scrollable message history,
   loading state while waiting for a response, and graceful error handling
   if the API call fails.

5. Guardrails: if the user asks something the underlying data can't answer
   (e.g. asks about a metric with no supporting columns), the LLM should say
   so explicitly rather than guessing.

When done, give me 5 example questions I can test in the chat, and tell me
how you're controlling token usage / cost per request.
```

---

## PHASE 6 — PDF Report Generation

```
Build Phase 6 of BizLens AI. Dashboard, AI insights, and chat (Phases 4-5)
are working.

SCOPE FOR THIS PHASE:

1. Implement `POST /reports/generate` (Python service):
   - Pull the latest metrics_snapshot and insights for a business.
   - Generate a PDF with these sections: Executive Summary, Revenue Analysis,
     Sales Analysis, Customer Analysis, Profitability, Key Trends, Risks,
     Recommended Actions, Next Month Priorities.
   - Use the LLM only to write the prose for each section from the verified
     metrics (same rule as always — no invented numbers). Use a Python
     PDF library (reportlab or weasyprint) for layout/generation.
   - Store the generated PDF in Blob storage and save the URL + metadata in
     the `reports` table.

2. Implement `GET /reports` and `GET /reports/{id}` to list and fetch past
   reports for a business.

3. Frontend: add a "Generate Report" button on the dashboard and a
   /dashboard/[businessId]/reports page listing past reports with download
   links.

4. Handle the case where report generation takes a while — show a progress/
   pending state rather than blocking the UI.

When done, generate one sample report end-to-end and tell me where to find
the PDF so I can review the formatting and content quality.
```

---

## PHASE 7 — Security Review + Deployment

```
Build Phase 7 of BizLens AI — the final hardening and deployment pass.
All features from Phases 1-6 work locally.

SCOPE FOR THIS PHASE:

1. Security review — check and fix as needed:
   - Every database query is scoped to the authenticated user's own
     businesses/datasets (no cross-tenant data leakage).
   - All secrets are in environment variables, never logged, never present
     in client-side bundles.
   - File upload validation: type, size limit, and safe handling of
     malformed/malicious files.
   - Rate limiting on /ai/chat and /reports/generate to control cost and
     abuse.
   - CORS on the Python service locked to the deployed frontend domain only.
   - HTTPS enforced everywhere.

2. Deployment prep:
   - Frontend: prepare for Vercel deployment — confirm build passes, list
     every environment variable Vercel needs.
   - Python service: prepare for Render or Railway deployment — provide a
     Dockerfile or equivalent, list every environment variable needed.
   - Neon: confirm the connection uses Neon's pooled connection string
     (important for serverless environments) and that migrations have a
     documented "how to run in production" step.

3. Give me a final pre-launch checklist covering: environment variables set
   correctly in each platform, database migrated, a full manual test of the
   entire flow (sign up -> create business -> upload -> dashboard -> chat ->
   report) on the deployed URLs, and a rollback plan if something breaks.

Do not add any new features in this phase — this is hardening and shipping
only.
```

---

## How to use this

1. Paste Phase 0 first and let the agent propose the plan — review it before continuing.
2. Paste Phase 1, test locally, confirm it works.
3. Move to Phase 2 only once Phase 1 is genuinely working — resist the urge to skip ahead.
4. Repeat through Phase 7.
5. If a phase's output doesn't match the spec, don't move on — tell the agent specifically what's wrong and have it fix that phase first. Compounding a broken foundation into later phases is the most common way vibe-coded projects fall apart.
