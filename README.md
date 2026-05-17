# GGPL Gasket Quote

Streamlit remains available during the migration:

```powershell
streamlit run apps/streamlit/app.py
```

The historical command is still supported through a compatibility wrapper:

```powershell
streamlit run app.py
```

Phase 0 monorepo layout:

- `apps/streamlit` - existing Streamlit app shell.
- `apps/api` - FastAPI scaffold with `/healthz` and OpenAPI at `/docs`.
- `apps/web` - Next.js 15 scaffold with Tailwind and shadcn/ui configuration.
- `packages` - moved Python business logic packages, preserving `core.*`, `data.*`, `domain.*`, and `services.*` imports.
- `infra` - local Docker Compose for API, worker, Redis, and Postgres.
