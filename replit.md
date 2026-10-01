# Jarvis 2

An AI trading dashboard and paper-trading backend imported from the Jarvis 2 GitHub repository.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm --filter @workspace/jarvis2 run dev` — run the Jarvis 2 dashboard preview
- `cd jarvis2/backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000` — run its FastAPI backend
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `jarvis2/frontend` — imported React/Vite trading dashboard
- `jarvis2/backend` — imported FastAPI service, agent logic, and SQLite-backed paper-trading data

## Architecture decisions

- The original repository is kept under `jarvis2/` with its Git history.
- Broker credentials are intentionally not configured; start locally in paper mode only.

## Product

The imported Jarvis 2 dashboard displays portfolio, trade, and agent information from its FastAPI backend.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

_Populate as you build — sharp edges, "always run X before Y" rules._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
