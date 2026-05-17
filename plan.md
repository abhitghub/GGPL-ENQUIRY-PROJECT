# GGPL Gasket Quote — Migration & World-Class Productization Plan

**Author:** Engineering planning session, 2026-05-15
**Owner:** raj.gandhi@eiconvision.com
**Status:** Proposed — awaiting approval to begin Phase 0

---

## 1. Executive Summary

The current Streamlit MVP has proven the business value of automated gasket quote
extraction. To scale GGPL from internal tool to a production-grade B2B product,
we will migrate to a modern decoupled architecture **without rewriting any
business logic**. The Python `core/` pipeline (extraction, rules, formatting,
PDF/Excel generation) is already well-isolated and migration-ready. The work is
almost entirely about replacing the Streamlit shell with a proper API + SPA, and
hardening the operational surface.

**Target architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│  Next.js 15 (App Router, RSC) + TypeScript + Tailwind       │
│  shadcn/ui · TanStack Table/Query · Zustand · react-hook-form│
│  Deployed to Vercel                                          │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST + SSE
┌──────────────────────────▼──────────────────────────────────┐
│  FastAPI (Python 3.11) — wraps existing core behavior       │
│  Pydantic v2 · SQLModel · Alembic · structlog               │
│  Celery workers for long-running extraction                 │
│  Deployed to Railway/Fly.io as 2 services (web + worker)    │
└──────────┬───────────────────────────────┬──────────────────┘
           │                               │
    ┌──────▼──────┐    ┌──────────┐    ┌──▼─────────┐
    │  Supabase   │    │  Redis   │    │  OpenAI    │
    │  Postgres + │    │  (Upstash│    │  GPT-4.1   │
    │  Auth +     │    │  cache + │    │  -mini     │
    │  Storage    │    │  queue)  │    │            │
    └─────────────┘    └──────────┘    └────────────┘
```

**Non-negotiables:**
- Zero feature regression. Every Streamlit feature listed in §3 must ship in the new app before sunset.
- The `core/`, `domain/`, and `services/extraction.py` modules remain the behavioral baseline. Phase 0 may move files and add import/config adapters, but no extraction, rules, formatting, or export behavior changes without golden-file/eval proof.
- LLM model stays `gpt-4.1-mini` (validated for multi-field extraction).
- Supabase remains the system of record (we already own the schema).
- All output (PDF/Excel) must be structurally and visually identical to current GGPL templates — customers receive these. (See Phase 4 for the diff harness; byte-equality is not a reliable acceptance criterion.)

**Total estimated effort:** 12–14 weeks for a single full-stack engineer, or ~9–10 weeks with one frontend + one backend running Phases 1 and 2 in parallel (Phase 3 onward remains the bottleneck — frontend-heavy with backend support).

---

## 2. Why Migrate (Pain Points Addressed)

| Streamlit pain | Production impact | Resolved by |
|---|---|---|
| Full-page rerun on every interaction | Janky UX, slow inline edits | React component-level reactivity |
| `st.session_state` lost on tab close | Users lose work | Server-side persistence + auto-save |
| No real auth or multi-tenancy | Cannot onboard a second customer | Supabase Auth + RLS per org |
| Long LLM calls block UI thread | App appears frozen for large files | Celery jobs + SSE progress streaming |
| Daemon-thread "background jobs" | Lost on container restart | Durable queue (Celery + Redis) |
| Pages-as-files multipage hack | No real routing, clumsy navigation | Next.js App Router |
| Mobile is unusable | Field engineers cannot quote on-site | Responsive design + PWA |
| Cannot embed in customer/ERP portals | Limits future integrations | API-first design |
| Single-process Streamlit container (no warm pool) | First request after idle is slow | Containerized API with warm Celery workers + autoscaling |
| Color-coding via inline CSS hacks | Brittle visual layer | Design tokens + accessible components |
| No A/B testing or progressive rollout | Cannot safely ship LLM/prompt changes | Feature flags + structured eval harness |

---

## 3. Feature Parity Inventory (Migration Acceptance Criteria)

Every item below must be functional in the new app before Streamlit is sunset.

### 3.1 Document Ingestion / Intake
- Customer name and project / PO reference captured before processing and carried into history + quote defaults.
- Email body paste (raw text)
- Excel upload (`.xlsx`/`.xls`, multi-sheet, merged-cell expansion)
- PDF upload (text-based, pdfplumber)
- Manual single-item entry form
- All quote-workspace ingestion paths append to the current working list rather than replacing it, unless the user explicitly clears / starts a new enquiry.
- Word document upload (`.docx`) is required for the Document Q&A assistant. Quote-workspace `.docx` extraction is additive and must use the same Smart Parse contract if implemented.

### 3.2 Extraction Pipeline (preserved verbatim from `core/`)
- GPT-4.1-mini chunked extraction (current baseline: 20 rows/chunk, 3 parallel workers)
- Live preview of items as chunks complete (streamed to UI)
- Progress bar with chunk-level granularity
- Redis cache (SHA256 keyed, 7-day TTL)
- Specific error surfacing (scanned PDF, rate limit, no items)
- Truncation warning beyond 400 rows

### 3.3 Working List / Data Grid
- Inline editing of all 50 GasketItem fields
- Status icons per row (ready/check/missing/regret)
- Color coding (green/amber/red/grey)
- Add blank row at end or after the selected row
- Multi-row selection with bulk delete
- Bulk edit selected rows or all visible rows across type, MOC, rating, face, groove, thickness, BHN, UOM, SW winding/filler/rings, and standard
- Reprocess edited customer descriptions through Smart Parse for selected / changed rows
- Mark selected rows as regret and preserve regret status through quote generation
- Filter by status
- Re-run rules + reformat on edit (debounced)
- Extraction summary (deduplicated specs)
- Missing-field clarification panel and downloadable RFI `.txt` draft email grouped by flag / line number

### 3.4 Quote Generation
- Buyer details form (buyer name/address, customer enquiry no, attention, designation, contact no, email)
- GGPL sales representative fields (name, designation, contact no, email)
- Quote reference (quote no, date, rev no, rev date)
- Currency selection (12 currencies) with editable FX rates
- Line item editor (qty override, UOM display, base INR unit price, converted unit price, total price, currency-aware)
- GST and discount controls (IGST / CGST+SGST / UGST, GST %, discount %, GST disabled for non-INR quotes)
- Terms and conditions fields: price basis, validity, packing, freight, payment terms, bank charges, delivery, inspection, insurance, HSN code, LD clause, cancellation, minimum order value
- Technical notes entered per quote
- PDF export matching GGPL template QT00102 R1
- Excel export matching GGPL official layout (10 columns, color-coded)
- Generated PDF is saved to quote history and downloadable from the dashboard/history row.
- Start New Enquiry clears working items, selected rows, generated output, quote form state, and input widgets.

### 3.5 History & Pipeline Dashboard
- All saved quotes (Supabase-backed)
- Search/filter by customer, project, stage, outcome
- Stage progression: initial → review → quote_prep → repricing → sent → po
- Stage history audit log (append-only)
- Stage metadata (PO number, outcome, free-form notes)
- Metrics: items processed, conversion rate, win rate, avg time-to-sent
- Gasket type distribution chart

### 3.6 Auxiliary Tools
- Unit converter (length, pipe size DN/NPS, pressure, rating, temperature, torque, force)
- Document Q&A assistant (PDF/Excel/Word/CSV/TXT upload + chat, including `.xlsm`)
- Floating gasket-domain chat widget (last 20 messages, gasket knowledge Q&A)

### 3.7 Operational
- API key entry via UI (alongside env-based config)
- Local JSON fallback when Supabase unavailable
- Reference data loaded once, cached (357 mappings, dim tables, ring tables)

---

## 4. Target Architecture (Detailed)

### 4.1 Repository Layout (Monorepo)

```
gasket-quote/
├── apps/
│   ├── api/                    # FastAPI service
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── routers/
│   │   │   │   ├── extraction.py
│   │   │   │   ├── quotes.py
│   │   │   │   ├── exports.py
│   │   │   │   ├── chat.py
│   │   │   │   ├── docs.py        # doc assistant
│   │   │   │   └── auth.py
│   │   │   ├── deps.py            # FastAPI dependencies
│   │   │   ├── middleware/        # auth, request-id, structured logging
│   │   │   ├── schemas/           # request/response Pydantic models
│   │   │   ├── services/          # imports from packages/core
│   │   │   ├── workers/           # Celery tasks
│   │   │   ├── db/                # SQLModel models, repositories
│   │   │   ├── auth/              # Supabase JWT verification
│   │   │   └── config.py          # pydantic-settings
│   │   ├── alembic/               # DB migrations
│   │   ├── tests/                 # pytest
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   └── web/                    # Next.js 15 app
│       ├── app/                # App Router
│       │   ├── (auth)/
│       │   ├── (dashboard)/
│       │   │   ├── quotes/
│       │   │   ├── history/
│       │   │   ├── tools/converter/
│       │   │   └── doc-assistant/
│       │   ├── api/            # BFF routes (proxy + auth)
│       │   └── layout.tsx
│       ├── components/
│       │   ├── ui/             # shadcn primitives
│       │   ├── grid/           # TanStack Table wrappers
│       │   ├── upload/
│       │   ├── quote/
│       │   └── chat/
│       ├── lib/
│       │   ├── api.ts          # typed API client (orval-generated)
│       │   ├── auth.ts
│       │   └── store/          # Zustand slices
│       ├── hooks/
│       ├── e2e/                # Playwright
│       ├── package.json
│       └── next.config.ts
├── packages/
│   ├── core/                   # MOVED from gasket-quote-mvp/core/ unchanged
│   ├── domain/                 # MOVED from gasket-quote-mvp/domain/
│   ├── services/               # MOVED legacy services; extraction behavior preserved
│   ├── data/                   # reference Excel files
│   ├── pyproject.toml          # editable install exposes core/domain/data/services imports
│   └── prompts/                # versioned LLM prompts (introduced after baseline eval)
├── infra/
│   ├── docker-compose.yml      # local dev (api + worker + redis + postgres)
│   ├── railway.toml            # production
│   └── github-actions/
├── evals/                      # LLM regression suite (see §10)
│   ├── fixtures/
│   └── run_eval.py
├── docs/
│   ├── architecture.md
│   ├── api.md                  # auto-generated from OpenAPI
│   └── runbook.md
└── README.md
```

**Why monorepo:** shared schema between FastAPI and Next.js (auto-generated TS
types from OpenAPI), single CI/CD pipeline, atomic cross-stack changes, easier
to reason about for a small team.

### 4.2 Backend (FastAPI)

**Framework choices and why:**
- **FastAPI** — first-class Pydantic v2 support (your domain model is already Pydantic), auto OpenAPI generation, async-native, mature ecosystem.
- **SQLModel** — Pydantic + SQLAlchemy in one. Lets us reuse the GasketItem schema for both DB rows and API responses with one definition.
- **Alembic** — proper schema migrations. The current `supabase_schema.sql` with `add column if not exists` patches is not sustainable.
- **Celery + Redis** — durable background jobs. Replaces the daemon-thread `services/jobs.py` which loses work on container restart.
- **structlog** — structured JSON logs with request IDs (essential for production debugging).
- **pydantic-settings** — typed config from env/files with validation at boot.

**Behavioral baseline from existing code (moved/imported in Phase 0):**
- `core/document_reader.py` (LLM extraction)
- `core/rules.py` (business rules)
- `core/formatter.py` (description formatting)
- `core/quote_exporter.py` (Excel)
- `core/quote_pdf.py` (PDF — must stay structurally identical, see Phase 4)
- `core/parser.py`, `core/unit_converter.py`
- `domain/models.py`
- `services/extraction.py` (orchestrator — `process_document` is invoked by Celery task)
- `data/reference_data.py`
- `services/storage.py` and `services/jobs.py` — kept untouched for the Streamlit app's continued use during the migration window.

Allowed Phase 0 changes to these modules are limited to import-path compatibility, configuration injection, and packaging. Prompt extraction/versioning is deferred until after the baseline eval and golden-output suite are passing, so prompt changes cannot be hidden inside the framework migration.

Import compatibility is a launch blocker. Existing absolute imports such as `from core.rules import apply_rules`, `from core.quote_pdf import build_quotation_pdf`, and `from services.extraction import process_document` must continue to work in Streamlit, FastAPI, Celery, pytest, and one-off scripts. Phase 0 must provide either an editable `packages/` install or root-level compatibility packages, then prove imports with compile/import smoke tests before and after the move.

**New code in `apps/api/` (does not modify the above):**
- `apps/api/app/db/repositories.py` — SQLModel-based persistence layer (the new system of record going forward).
- `apps/api/app/workers/extraction_task.py` — Celery task wrapper around `services/extraction.process_document`. Replaces the `services/jobs.py` daemon-thread pattern for the new app, but the legacy `services/jobs.py` stays in place for Streamlit until cutover.
- After Phase 8 cutover, both `services/storage.py` and `services/jobs.py` are deleted (Streamlit is sunset).

**Output preservation rule:** `core/quote_pdf.py` and `core/quote_exporter.py` are template engines, not implementation details. The migration may wrap them, queue them, or store their output differently, but must not replace their layout logic with browser print, HTML-to-PDF, jsPDF, a new ReportLab template, or a reimplemented Excel layout unless the diff harness proves exact parity and GGPL signs off.

### 4.3 Frontend (Next.js)

**Framework choices and why:**
- **Next.js 15 App Router** — server components reduce JS bundle, built-in routing, edge-ready, Vercel-native.
- **TypeScript strict mode** — types and TanStack Query hooks generated from FastAPI's OpenAPI schema via `orval`. Backend changes break frontend compile, not runtime.
- **shadcn/ui** — copy-in components (we own the source), built on Radix primitives for accessibility, Tailwind-based.
- **TanStack Table** — replaces `st.data_editor`. Headless, virtualized, supports inline editing, column resizing, sorting, filtering, row selection. Handles 10k rows smoothly.
- **TanStack Query** — server state with caching, optimistic updates, polling, SSE integration.
- **Zustand** — minimal client state (UI state only — server state lives in TanStack Query). Replaces the 13 `st.session_state` keys catalogued in §7.
- **react-hook-form + Zod** — form state and validation, Zod schemas mirror backend Pydantic schemas via codegen.

### 4.4 Authentication & Multi-Tenancy

**Supabase Auth** (already in stack — no new vendor):
- Email/password + Google SSO (confirm GGPL's identity provider before Phase 2).
- JWT in httpOnly cookie issued by Supabase, verified by FastAPI via `python-jose`/JWKS.
- New tables: `organizations`, `org_members(user_id, org_id, role)` (roles: `owner`, `editor`, `viewer`).
- FastAPI resolves the authenticated user to an active `org_id` before any repository call. Every repository method requires `org_id` explicitly and includes it in `WHERE` clauses.
- SQLAlchemy/SQLModel will not implicitly populate Supabase `auth.uid()`. If the API connects directly to Postgres, tenancy is enforced first in the API repository layer. RLS remains a second guard for Supabase client access and is tested separately.
- If we choose to enforce RLS for direct SQL connections too, the API must set request claims/session variables at the start of each transaction and include an integration test proving cross-org reads/writes fail.
- `quotes.org_id` and `created_by` are introduced as nullable during the compatibility window, backfilled, then made `not null` after Streamlit is read-only.

### 4.5 File Storage

- Generated PDFs and Excels stored in **Supabase Storage** under `quotes/{org_id}/{quote_id}/`.
- DB stores only the storage path, not base64. The current `quote_pdf_b64` column is a 200 KB blob per quote — this won't scale and bloats every list query.
- Signed URLs (1-hour expiry) returned to the frontend for download.

### 4.6 Real-Time Extraction Streaming

- Frontend uploads file → API returns `job_id` immediately.
- Frontend opens an **SSE connection** to `GET /jobs/{job_id}/stream`.
- Celery worker publishes events to Redis pub/sub (`job:{job_id}`):
  - `progress` (current_chunk, total_chunks)
  - `chunk_items` (newly extracted items — feeds live preview grid)
  - `complete` (final results)
  - `error` (typed error code)
- API forwards Redis events to the SSE stream.
- Reconnection-safe (event IDs let frontend resume after network blip).

### 4.7 Observability

- **Sentry** — errors AND performance traces, both backend and frontend. Sentry's tracing covers the API → Celery → OpenAI hops we care about; OpenTelemetry is deferred until we outgrow Sentry's tracing (likely never at this scale).
- **PostHog** — product analytics (which features get used, funnel from upload → quote sent).
- **Health endpoints** — `/healthz` (liveness), `/readyz` (DB + Redis + OpenAI reachable).
- **Structured logs** — JSON with request_id, user_id, org_id, job_id correlation via structlog.

---

## 5. Data Model Evolution

### 5.1 Current → Target Schema

**New tables:**
```sql
-- Multi-tenancy
organizations (id, name, slug, created_at, plan, settings jsonb)
org_members (org_id, user_id, role, created_at)

-- Async work tracking (replaces daemon-thread state)
extraction_jobs (
    id uuid pk,
    org_id uuid fk,
    user_id uuid fk,
    quote_id uuid fk null,
    source_type text,        -- email | excel | pdf | docx
    source_path text,        -- supabase storage path
    status text,             -- queued | running | completed | failed
    progress jsonb,          -- {current_chunk, total_chunks}
    error_code text,
    error_message text,
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz default now()
)

-- Audit log (for SOC2-readiness later)
audit_events (
    id bigserial pk,
    org_id uuid,
    user_id uuid,
    event_type text,         -- quote.created | quote.stage_changed | export.downloaded | ...
    entity_type text,
    entity_id uuid,
    metadata jsonb,
    created_at timestamptz default now()
)

-- Versioned LLM prompts
prompts (
    id uuid pk,
    name text,               -- e.g. 'extraction_system_v1'
    version int,
    content text,
    metadata jsonb,
    is_active boolean,
    created_at timestamptz
)

-- Per-org reference data overrides (future)
reference_overrides (org_id, ref_type, key, value, updated_at)

-- Chat sessions (gasket-domain widget + doc assistant)
chat_sessions (
    id uuid pk,
    org_id uuid fk,
    user_id uuid fk,
    kind text,               -- 'gasket_widget' | 'doc_assistant'
    title text,
    document_id uuid null,   -- present for doc_assistant sessions
    created_at timestamptz default now(),
    updated_at timestamptz
)
chat_messages (
    id uuid pk,
    session_id uuid fk,
    role text,               -- 'user' | 'assistant' | 'system'
    content text,
    metadata jsonb,          -- token counts, error flag, citations
    created_at timestamptz default now()
)
```

**Modified tables:**
```sql
-- quotes table
+ org_id uuid null          -- nullable until legacy rows and Streamlit compatibility are resolved
+ created_by uuid null      -- nullable until auth is mandatory for all writes
+ updated_at timestamptz
+ version int not null default 1  -- optimistic concurrency for dual-app transition
+ pdf_storage_path text     -- replaces quote_pdf_b64 (deprecated, kept for migration)
+ source_doc_path text      -- original uploaded file
+ quote_pdf_b64 text        -- kept read-compatible until final cleanup migration
```

**Indexes:**
- `quotes(org_id, created_at desc)` — primary list query
- `quotes(org_id, customer)` — search
- `quotes(org_id, stage)` — pipeline view
- `extraction_jobs(org_id, status, created_at desc)`
- `audit_events(org_id, created_at desc)`

### 5.2 Migration Strategy

- All schema changes via **Alembic**, applied in order.
- Compatibility migration first: add nullable `org_id`, nullable `created_by`, `updated_at`, `version`, `pdf_storage_path`, and `source_doc_path` without breaking the existing Streamlit writer.
- Backfill script: create the default GGPL org, assign existing rows to it, decode `quote_pdf_b64` → upload to Supabase Storage → set `pdf_storage_path`.
- During parallel run, legacy Streamlit writes are either restricted to internal users only or routed through a compatibility path that sets the default org and increments `version`.
- New API writes use optimistic concurrency (`version`) so stale edits are rejected instead of silently overwriting quote data.
- Cleanup migration only after Streamlit is read-only: enforce `org_id not null`, enforce `created_by not null` for new rows, remove legacy base64 reads, then drop `quote_pdf_b64`.
- Forward-compatible: deploy schema changes before code changes; deploy code; run backfill; then run cleanup migrations after cutover signoff.

---

## 6. Migration Phases

Each phase is **independently deployable** and produces tangible value. The current Streamlit app keeps running until Phase 8 cutover.

### Phase 0 — Foundation (Week 1)
Goal: repo skeleton, CI/CD, dev environments work end-to-end.

- Create monorepo layout (§4.1).
- Move `core/`, `domain/`, `data/` into `packages/` without behavior changes. Update existing Streamlit imports to point at new locations (proves nothing broke).
- Add package/install wiring so legacy absolute imports still resolve for Streamlit, API, Celery workers, tests, and export scripts.
- `apps/api/` FastAPI scaffold with `/healthz`, OpenAPI at `/docs`.
- `apps/web/` Next.js 15 scaffold with shadcn/ui installed and a single login-redirect page.
- Docker Compose for local dev (api + worker + redis + postgres).
- GitHub Actions CI: pytest, eslint, tsc, build check, Docker image push.
- Sentry + PostHog SDKs wired (no-op until later).
- Streamlit app remains shippable from `apps/streamlit/` (renamed `app.py`).

**Acceptance:** `python -m compileall app.py core tests ui` passes before the move; the equivalent compile/import smoke test passes after the move; `docker compose up` brings the stack online locally; CI green on a no-op PR.

### Phase 1 — Backend API Parity (Weeks 2–3)
Goal: every Streamlit-facing operation has a typed REST endpoint.

- Pydantic request/response schemas (TypeScript types and TanStack Query hooks auto-generated via `orval`).
- Endpoints:
  - `POST /api/v1/extractions` — upload file or post text, returns `job_id` (202 Accepted).
  - `GET /api/v1/jobs/{id}` — poll status.
  - `GET /api/v1/jobs/{id}/stream` — SSE.
  - `GET/POST/PATCH/DELETE /api/v1/quotes` (CRUD).
  - `POST /api/v1/quotes/{id}/items/bulk` (bulk edits — accepts a partial diff).
  - `POST /api/v1/quotes/{id}/items/bulk-recompute` (re-runs `apply_rules` + `format_description` on a batch of dirty rows; returns full updated rows).
  - `POST /api/v1/quotes/{id}/items/reprocess-text` (re-runs Smart Parse on selected / changed customer descriptions).
  - `POST /api/v1/quotes/{id}/rfi-draft` (returns grouped clarification text for missing fields).
  - `POST /api/v1/quotes/{id}/exports/pdf` and `/exports/xlsx` (returns signed URL).
  - `POST /api/v1/quotes/{id}/stage` (advance stage with reason).
  - `GET /api/v1/quotes/{id}/history` (stage history).
  - `GET /api/v1/dashboard/metrics`.
  - `POST /api/v1/chat/completions` (gasket-domain chat — proxy with system prompt).
  - `POST /api/v1/doc-assistant/sessions` and `POST /api/v1/doc-assistant/sessions/{id}/messages`.
  - `POST /api/v1/converter/{type}` (pure functions, no DB).
- Celery worker invokes `process_document()` from existing `services/extraction.py`. Publishes progress to Redis pub/sub.
- Alembic baseline migration matching current Supabase schema; second migration adds compatibility-safe `org_id`, `created_by`, `version`, `extraction_jobs`, and `audit_events`.
- Auth/tenancy tests prove that a user in org A cannot read, edit, export, or stream jobs from org B through the API.
- Backend pytest suite covers every endpoint; reuses existing `tests/test_pipeline.py`.

**Acceptance:** A curl-based script can replicate the full Streamlit workflow (upload → extract → edit → export PDF/Excel → save quote → advance stage). Existing `tests/test_pipeline.py` passes against the new package locations.

### Phase 2 — Frontend Foundation (Weeks 3–4, parallel with Phase 1)
Goal: design system, auth, shell navigation.

- Tailwind config with GGPL brand tokens (extract from current `ui/styles.py`).
- shadcn/ui components installed: button, input, select, dialog, dropdown-menu, tabs, table, card, badge, sheet, sonner (toast).
- App shell: top nav, sidebar, breadcrumbs, user menu.
- Supabase Auth integration: login, magic-link, Google SSO, password reset.
- Route guards (server-side via middleware.ts).
- Empty states for: dashboard, quote list, history.
- Light/dark theme toggle (system default).
- Fully responsive (mobile + tablet breakpoints). Wireframe in Figma first if a design resource is available; otherwise Tailwind defaults are acceptable for Phase 2 and can be polished in Phase 7.

**Acceptance:** A user can sign up, log in, see an empty dashboard, log out. Lighthouse score ≥ 90 on shell pages.

### Phase 3 — Core Workflow: Upload → Extract → Edit (Weeks 5–6)
Goal: the most-used path works end-to-end with better UX than Streamlit.

- **Upload** — drag-drop zone with file-type detection, size limit, paste-text mode (for emails), file preview before submit.
- **Intake context** — customer name and project / PO reference are captured before extraction, defaulted into the quote form, and saved with the history entry.
- **Append semantics** — processing another email/file/manual row adds to the current working list; clear/start-new is the only replacement path.
- **Extraction view** — full-page progress with chunk-level granularity, live-preview grid populating as chunks complete (driven by SSE).
- **Processing stubs** — an extraction job appears immediately in history/dashboard as `processing`, then updates in place when extraction completes.
- **Working list (data grid)** — TanStack Table with:
  - All 50 GasketItem fields as columns (default visible: 12; rest behind column-picker).
  - Inline editing (cell-level, with Tab navigation).
  - Status badges (ready/check/missing/regret) with tooltips explaining the flag.
  - Color-coded row backgrounds (accessible — color is supplementary, badge is primary signal).
  - Add row, select all, deselect all, multi-row select, bulk delete, bulk edit, bulk re-extract / reprocess text, and bulk status filter.
  - Regret toggle for selected rows; regret items remain in the list and appear as regret in exports.
  - Virtualized rows (handles 10k+ items).
  - Column resize, reorder, hide/show, persisted to user prefs.
  - Optimistic updates with rollback on API error.
  - Auto-save (debounced 1s after edit).
- **Clarifications** — missing-field flags render as a grouped action list and a downloadable RFI text draft.
- **Recompute** — edits are queued and **batched**: when the user pauses for 500ms, all dirty rows are sent in one `POST /quotes/{id}/items/bulk-recompute` call. Server applies `apply_rules()` + `format_description()` and returns the updated rows. This avoids per-cell round trips while keeping the UI in sync. (Rationale: business logic stays Python — we do not duplicate `rules.py`/`formatter.py` in TypeScript.)

**Acceptance:** Power user can process a 200-row Excel and edit ten cells faster than in Streamlit. SUS score ≥ 80 from three GGPL test users.

### Phase 4 — Quote Generation & Exports (Weeks 7–8)
Goal: PDF and Excel outputs are structurally and visually equivalent to current GGPL templates.

- Quote workspace page: split layout (line items left, quote-meta panel right).
- Buyer details form (autocomplete from past customers) with the exact current fields: buyer name/address, customer enquiry no, attention, designation, contact no, email.
- GGPL sales representative fields: name, designation, contact no, email.
- Quote reference fields: quote no, quote date, revision no, revision date.
- Currency picker with editable FX rate (rate snapshot frozen on quote save). INR remains fixed at 1.0; non-INR quotes show tax/duty rather than GST.
- Pricing editor preserves current behavior: user edits INR base unit price and quantity; quote-currency unit price and totals are calculated from the selected conversion rate.
- GST/discount controls preserve current behavior: discount applies before tax; GST applies only to INR; supported GST modes are IGST, CGST+SGST, and UGST.
- Terms/notes preserve every current PDF-affecting field: price basis, validity, packing, freight, payment terms, bank charges, delivery, inspection, insurance, HSN code, LD clause, cancellation, minimum order value, and technical notes.
- PDF preview pane (generated on-demand via signed URL, iframe-rendered).
- Excel download button (generated on-demand, signed URL).
- Both `core/quote_pdf.py` and `core/quote_exporter.py` invoked unchanged via Celery task → file uploaded to Supabase Storage → signed URL returned.
- **PDF template lock** — the generated PDF must continue to use `build_quotation_pdf()` from `core/quote_pdf.py` with the existing `logo.png` asset and current ReportLab layout. Header, company block, quote/revision fields, PAN/CIN/GSTIN, buyer block, item table columns, page-turn behavior, totals/GST block, terms, technical notes, general terms, signature block, footer text, fonts, margins, borders, and pagination are frozen unless a signed-off template change is explicitly requested.
- **Diff test** — structural/visual comparison against current Streamlit output:
  - **Excel:** compare via `openpyxl` cell-by-cell + number formats + style hash + sheet dimensions. Target: zero structural/style diffs. Byte identity is a nice-to-have, not a requirement.
  - **PDF:** byte-identical is impractical (reportlab embeds creation timestamp, font cache id, etc.). Use `pdfplumber` text extraction + image-diff (per-page rasterized PNG with `pdf2image`) with a <1% pixel tolerance. Target: text 100% match, visual diff <1%.

**Acceptance:** Ten real customer quotes generated through new app pass the diff harness, including at least one multi-page quote, one INR quote with GST/discount, one non-INR quote, one quote with regret rows, and one quote with long terms/technical notes. GGPL operations team visually confirms PDFs are indistinguishable on three sample quotes.

### Phase 5 — History & Pipeline Dashboard (Week 9)
Goal: full pipeline visibility and quote management.

- Quote history page: searchable table, filters (customer, stage, date range, owner).
- Quote detail page: read-only view + "Resume" button to re-open in workspace.
- Pipeline kanban view (initial → review → quote_prep → repricing → sent → po) with drag-to-advance.
- Stage advancement modal: required fields per stage (e.g. PO number when moving to `po`).
- Audit log per quote (stage history + edit history from `audit_events`).
- Dashboard metrics: items processed (week/month), conversion rate (sent/total), win rate (po/sent), avg time-to-sent, gasket type distribution chart (recharts).

**Acceptance:** Existing Streamlit dashboard data renders identically in new app. Sales lead can find any quote in <10 seconds.

### Phase 6 — Chat & Doc Assistant (Week 10)
Goal: feature parity for assistive tools, with one targeted enhancement.

- Floating gasket-domain chat widget (bottom-right FAB, modal panel, last 20 messages).
- Persisted chat history per user (`chat_sessions` + `chat_messages` tables from §5).
- Doc assistant page (parity): PDF, DOCX, XLSX, XLS, XLSM, CSV, and TXT upload + threaded chat that sends the whole doc text as context each turn — same behavior as current Streamlit. Ships first to lock in parity.
- Doc assistant sidebar parity: loaded document list, remove single document, clear all/reset, quick-question buttons, large-file warning, and clear conversation.
- **Enhancement (stretch, only if time permits):** chunk + embed uploaded doc with `text-embedding-3-small` into Supabase pgvector, switch to retrieval-augmented chat. Improves quality on 10+ page PDFs and reduces token cost. If skipped, deferred to backlog.
- Unit converter page: tabs per category, real-time conversion, copy-to-clipboard.

**Acceptance:** Chat answers gasket questions with same quality as current Streamlit chat. Doc assistant matches current behavior; if RAG enhancement shipped, must outperform current implementation on a 5-question eval set.

### Phase 7 — Production Hardening (Week 11)
Goal: ready for real customers and 99.5% uptime.

- **Security**
  - HTTPS-only, HSTS, CSP headers.
  - Rate limiting per user/org (slowapi on FastAPI).
  - File upload virus scanning (ClamAV in worker container).
  - Signed URLs with short expiry; never expose raw storage paths.
  - Pen-test the auth flow and quote isolation across orgs.
  - Secrets in Railway/Vercel env vars; never in repo (verify with gitleaks in CI).
- **Performance**
  - DB query budget: <100ms p95 for list queries (verify with explain analyze).
  - LLM call budget: <90s p95 for 100-row docs.
  - Capacity plan before load testing: document expected chunks/job, Celery worker concurrency, OpenAI RPM/TPM limits, Redis connection limits, retry/backoff behavior, and queue wait-time budget. The target is calibrated against the actual OpenAI project limits before being used as a launch gate.
  - Frontend Lighthouse perf ≥ 90 on key pages.
  - Image optimization, font subsetting.
  - Edge caching for static reference data.
- **Reliability**
  - Celery retries with exponential backoff and dead-letter queue.
  - Idempotency keys on POST /extractions (prevent duplicate jobs on user double-click).
  - Database backups: Supabase daily PITR (verify restore procedure).
  - Status page (statuspage.io free tier or self-hosted).
- **Observability**
  - Sentry alerts on error spike, P0/P1 to PagerDuty.
  - PostHog dashboards: weekly active orgs, funnel, retention.
  - Synthetic uptime checks every 5 min (UptimeRobot free tier).
- **Compliance prep** (not required for launch but design now):
  - Audit log already in schema.
  - PII inventory documented.
  - Data residency note (Supabase region selection).

**Acceptance:** Capacity model is documented, load test passes at the agreed launch concurrency without exceeding OpenAI/Redis limits, p95 extraction latency for a 100-row document is <90s once a job starts processing, pen test shows no critical or high findings, and runbook is documented.

### Phase 8 — Beta & Cutover (Weeks 12–13)
Goal: zero-downtime sunset of Streamlit.

- **Week 12: Parallel run.** Both apps live. New app behind feature flag for select beta users (GGPL ops team). Daily syncs to capture feedback. Bug-bash at end of week.
- **Week 13: Migration.** Backfill `org_id` on existing quotes. Migrate base64 PDFs to Supabase Storage. Switch DNS / public link to new app. Streamlit kept read-only for 2 weeks as fallback.
- **Post-cutover:** Streamlit container shut down on whatever host it currently runs on. Monorepo's `apps/streamlit/` archived (kept in git history, not deployed). Decommission the legacy hosting environment.

**Acceptance:** Two weeks of operation with new app only, zero Sev-1 incidents, GGPL ops team prefers new app over Streamlit (formal signoff).

---

## 7. State Management Mapping

A faithful translation of every `st.session_state` key to its new home:

| Streamlit key | Type | New home |
|---|---|---|
| `working_items` | List of dicts (current quote) | Server: `quotes.items` jsonb. Client: TanStack Query cache, optimistic updates. |
| `run_history` | List of past quotes | Server: paginated `GET /quotes`. Never load all 100 client-side. |
| `_quote_data` | Quote form values | Server: `quotes.quote_data`. Client: react-hook-form, auto-saved. |
| `_quote_excel` | Misnamed current generated PDF bytes in quote page | Server: Supabase Storage PDF object. Client: signed URL / dashboard download. Rename in new app to `generated_pdf` to avoid carrying the bug forward. |
| `quote_pdf_b64` / generated PDF bytes | Generated quotation PDF stored in history | Server: Supabase Storage path during/after migration. Compatibility read from `quote_pdf_b64` until cleanup. Client: signed URL or direct dashboard download. |
| `chat_messages` | Chat history | Server: `chat_sessions` table (per user). |
| `_selected_rows` | Set of row indices | Client: Zustand UI slice. |
| `filter_mode` | Status filter | Client: URL search params (so filters are bookmarkable). |
| `_show_quote_page` | Toggle | Client: route (`/quotes/[id]/generate`). |
| `_show_confirm` | Confirm dialog | Client: shadcn AlertDialog component state. |
| `_input_reset_seq` | Form reset trigger | Eliminated — react-hook-form `reset()`. |
| `chat_open`, `chat_loading` | Chat UI state | Client: Zustand UI slice. |
| `_bulk_df` | Working data-grid copy | Eliminated — TanStack Table is source of truth, edits flow through optimistic mutations. |
| `_pending_stage_{idx}` | Stage change confirm | Client: dialog state. |
| `_active_hist_entry` | Processing/current quote history row | Server: quote/job record linked to current workspace; updates in place as extraction, review, and quote generation progress. |
| `_last_excel`, `_last_filename` | Legacy generated Excel download state | Eliminated in favor of export records + signed URLs; if still exposed at cutover, mapped to Supabase Storage. |

---

## 8. LLM Strategy & Prompt Operations

The current setup hardcodes the system prompt in `core/document_reader.py`. For
production we treat prompts as code with versioning, evals, and gradual rollout.

- **Versioning** — prompts moved to `packages/prompts/` as YAML files with `id`, `version`, `content`, `model`, `temperature`, `created_at`. Loaded into the `prompts` DB table on startup.
- **A/B testing** — `extraction_jobs.prompt_id` records which prompt version processed each job. Compare extraction quality across versions.
- **Eval harness** (`evals/`) — golden set of 50 real customer documents (collected from current production usage with PII scrubbed). Each prompt change must run the eval and report:
  - Field-level accuracy (per GasketItem field).
  - Status distribution (% ready/check/missing/regret).
  - Avg latency, cost per doc.
  - Diff from previous version (regressions highlighted).
- **Model strategy unchanged** — `gpt-4.1-mini` stays the default. The eval harness lets us safely evaluate `gpt-4.1`, `claude-haiku-4-5`, etc. when they become attractive.
- **Cost tracking** — each LLM call logged with token counts; weekly cost dashboard per org (foundation for future per-tenant billing).

---

## 9. Future-Proofing (Designed In, Not Built Yet)

The architecture is shaped to make these natural additions, not bolt-ons:

- **Email-in ingestion** — SendGrid Inbound Parse → POST /extractions. Already supported by job queue.
- **Outlook/Gmail add-in** — OAuth flow via Supabase Auth, REST API already org-scoped.
- **ERP integration** (SAP, Tally, Zoho) — `quotes` already has stable IDs. Add `POST /webhooks/outbound` for stage-change events.
- **Customer self-service portal** — second Next.js app sharing the API, scoped to a `customer` role with read-only access to their own quotes.
- **Pricing engine** — currently manual. Add `pricing_rules` table and a `POST /quotes/{id}/price` endpoint that returns suggested prices; UI accepts/rejects.
- **Approval workflows** — `quotes.requires_approval`, `approval_chains` table. Stage transitions check policy.
- **Bulk operations API** — `POST /quotes/bulk` for partner/distributor batch uploads.
- **Other gasket types / non-gasket products** — `gasket_type` is already a discriminator; the formatter dispatches by type. New types add a formatter and a prompt section.
- **Multi-language UI** — Next.js i18n routing planned from Phase 2 (English only at launch, but no rework needed to add Hindi/Arabic later).
- **Mobile-first quoting** — responsive design from Phase 2; PWA installable in Phase 7.
- **Embeddings + RAG over quote history** — pgvector enabled in Phase 6 for doc assistant; same infra serves "find similar past quote" later.

---

## 10. Testing Strategy

| Layer | Tool | Coverage target | When it runs |
|---|---|---|---|
| Unit (backend) | pytest | 80% on `core/`, 100% on `rules.py` and `formatter.py` | Every PR |
| Unit (frontend) | Vitest + React Testing Library | 70% on hooks/utils | Every PR |
| Integration (backend) | pytest + testcontainers (postgres + redis) | All API endpoints exercised | Every PR |
| Contract | Pact or Schemathesis (fuzz against OpenAPI) | All endpoints fuzzed | Nightly |
| E2E | Playwright | 10 critical user journeys | Pre-deploy + nightly |
| Visual regression | Playwright + Percy | All key pages | Pre-deploy |
| LLM eval | Custom harness (`evals/`) | 50-doc golden set | Pre-prompt-change + weekly |
| Load | k6 | Calibrated launch concurrency from Phase 7 capacity model | Pre-major-release |
| Output diff | Golden-file (PDF/Excel) | Every quote-export endpoint | Every PR |

---

## 11. Operational Plan

### 11.1 Deployment

- **Backend (FastAPI + Celery worker):** Railway. Two services from one Dockerfile (different start commands). Auto-deploy from `main` after CI passes. Preview environments per PR.
- **Frontend:** Vercel. Auto-deploy from `main`. Preview deployments per PR (URL posted as PR comment).
- **DB / Auth / Storage:** Supabase (current account, upgrade to Pro plan for daily backups and 8 GB storage — ~$25/mo).
- **Cache + Queue:** Upstash Redis (serverless, free tier covers MVP, predictable scaling cost).
- **DNS:** Cloudflare (proxy, WAF, free tier).

### 11.2 Cost Estimate (Monthly)

| Service | Tier | Cost |
|---|---|---|
| Vercel | Pro (required — Hobby tier prohibits commercial use) | $20 |
| Railway | Starter + usage | ~$20 |
| Supabase | Pro (daily backups, 8 GB storage, 100 GB bandwidth) | $25 |
| Upstash Redis | Pay-as-you-go | $0–10 |
| OpenAI API | gpt-4.1-mini, ~1000 docs/mo (~30K tokens/doc) | $15–50 |
| Sentry | Developer (free) — upgrade to Team ($26) when error volume exceeds free quota | $0–26 |
| PostHog | Free tier (1M events) | $0 |
| Cloudflare | Free | $0 |
| **Total** | | **$80–150/month** |

### 11.3 Runbook (created in Phase 7)

- How to restore from backup.
- How to roll back a deploy.
- How to reprocess a failed extraction job.
- How to investigate "extraction took too long" complaints.
- How to handle OpenAI rate-limit incidents.
- On-call rotation (initially: one engineer, escalate to founder).

---

## 12. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| PDF/Excel template regressions | Medium | High (customer-facing) | Keep current Python export builders as the template source; golden-file tests in CI; visual diff sample reviewed by ops weekly |
| Hidden quote-field loss during UI rewrite | Medium | High | Quote form parity checklist covers every current `quote_data` field; export tests include GST, non-INR, regret rows, long terms, and multi-page PDFs |
| Frontend dev velocity (if React experience is limited) | Medium | Medium | Hire React contractor for Phases 2–4; or use v0.dev / shadcn examples to scaffold UI |
| Supabase RLS misconfigured → cross-tenant leak | Low | Critical | Defense-in-depth: API enforces org-scoping AND RLS; pen test before launch |
| Celery worker memory leaks on long jobs | Medium | Medium | Worker `--max-tasks-per-child=50` recycles processes; monitored in Sentry |
| OpenAI API outage | Low | High | Circuit breaker + queue retention; user-visible degraded-mode banner |
| Streamlit users resist change | Medium | Medium | Beta with ops team in Phase 8; parallel run for 2 weeks; training session |
| Scope creep (new features mid-migration) | High | High | Phases 0–8 are feature-frozen against §3 inventory; new work goes in §9 backlog |
| Reference data updates (new gasket types) mid-migration | Medium | Low | Reference data lives in `packages/data/`, shared between Streamlit and new app — single source of truth |

---

## 13. Decision Log

Decisions made during planning that should not be relitigated without explicit reason:

1. **Keep Python backend.** Rewriting `core/` in TypeScript would discard 7800+ lines of validated business logic and the Pydantic schema. No.
2. **FastAPI over Django.** API-first product, no need for Django's ORM/admin/templates.
3. **Next.js over Refine/Remix.** Largest ecosystem, Vercel-native, RSC reduces bundle, App Router is the future.
4. **Supabase over Postgres+Auth0+S3.** Already in stack; one vendor for DB+Auth+Storage simplifies ops at this scale.
5. **Celery over Arq/RQ/Dramatiq.** Most mature, best monitoring (Flower), broadest documentation; Arq is lighter and async-native — revisit if Celery's sync model causes friction.
6. **TanStack Table over AG-Grid.** AG-Grid is more powerful but commercial; TanStack handles our needs and is free + headless.
7. **Monorepo over polyrepo.** Shared schema (OpenAPI → TS) is the killer feature; small team → polyrepo coordination cost is too high.
8. **Phased migration over big-bang.** Streamlit stays live until Phase 8; protects revenue; lets us course-correct.
9. **gpt-4.1-mini retained.** Validated by the current implementation and protected by the eval harness. Reconsider quarterly or when pricing/quality materially changes.
10. **Compatibility-first dual app period.** `apps/api/` uses SQLModel against the same Supabase Postgres while Streamlit remains live. This is safe only with compatibility migrations, default-org backfill, optimistic concurrency, and restricted beta access. We do not rely on the assumption that one user will only write from one app. After Phase 8 cutover, Streamlit is read-only, then legacy `services/storage.py` / `services/jobs.py` paths and `quote_pdf_b64` are removed.

---

## 14. Definition of Done (for the migration as a whole)

The migration is complete when **all** of the following are true:

- [ ] Every feature in §3 works in the new app, verified by GGPL ops team signoff.
- [ ] All `tests/test_pipeline.py` and `tests/test_e2e.py` cases pass after being relocated to `apps/api/tests/` and pointed at the new package paths.
- [ ] Quote form parity checklist covers every current `quote_data` field and every PDF-affecting field has an automated export fixture.
- [ ] Excel exports: zero structural diff across 10 sample quotes. PDF exports: text 100% match, visual diff <1% across the same 10 quotes, including multi-page, INR/GST, non-INR, regret-row, and long-terms cases.
- [ ] Existing PDF quotations generated by Streamlit remain downloadable during migration, and newly generated PDFs are stored/downloaded without changing visible output.
- [ ] Two weeks of operation on new app only, zero Sev-1 incidents.
- [ ] p95 latency: extraction <90s for 100-row docs; UI interaction <200ms.
- [ ] Lighthouse perf ≥ 90 and accessibility ≥ 95 on key pages.
- [ ] Sentry and PostHog reporting data; structured logs queryable.
- [ ] Runbook reviewed in a tabletop exercise (simulated OpenAI outage and DB failover).
- [ ] Streamlit container shut down; DNS pointing only at new app.
- [ ] Architecture, API, and ops docs published in `docs/`.
- [ ] Cost tracking dashboard shows actual spend within 20% of estimate in §11.2.

---

## 15. Immediate Next Actions

If approved, the first week (Phase 0) breaks down as:

1. **Day 1** — Create monorepo skeleton; move `core/`, `domain/`, `data/` to `packages/`; verify Streamlit still runs.
2. **Day 2** — FastAPI scaffold with `/healthz`, `/docs` (OpenAPI), Pydantic settings.
3. **Day 3** — Next.js 15 scaffold with shadcn/ui, Tailwind, base layout.
4. **Day 4** — Docker Compose for local dev (api + worker + redis + postgres).
5. **Day 5** — GitHub Actions CI for backend (pytest) and frontend (lint + build).
6. **Day 6–7** — Sentry + PostHog wiring, environment variable management, README updated, kickoff meeting on Phase 1 scope.

After Phase 0, real customer-facing work begins in Phase 1 and the new app starts taking shape.
