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
- Broker credentials belong only in Replit Secrets, never chat, frontend code, Git, or logs. Dhan/OANDA connections are market-data-only; all execution is simulated paper trading.

## Requested operating rules

1. Continue monitoring and working toward a 90% or higher success ratio in each segment. Treat this as an aspirational target, never a guaranteed outcome or a reason to fabricate results.
2. Do not abandon a segment just because a strategy loses. Review all trades daily, research alternatives, backtest on genuine historical/provider data, and validate a replacement before applying it. Strategy-review and automatic-upgrade capabilities must not be claimed until implemented and verified.
3. Never change the created dashboard for any reason unless the user explicitly replaces this instruction. Keep the current frontend design and behavior intact.
4. Paper-capital allocation may be calculated automatically in pursuit of the performance target. Never allocate real funds, place real orders, hide losing trades, or manipulate the denominator to meet the target.
5. Develop an evidence-based self-learning process for this platform. Synthetic test fixtures may test software but must never enter trade history or performance claims.
6. Retain all trade data, including losses, for month-end analysis. Do not prune, reset, or rewrite history. Full-history snapshots and month-filtered exports must include provider provenance and distinguish legacy/unverified records. Local snapshots are not offsite disaster recovery.

## Evidence and runtime constraints

- Real market prices only for recorded paper trades. No sample/fake trades or estimated option premiums presented as live.
- Report verified closed-trade sample sizes, net P&L and losses alongside win rate. A claimed target requires sufficient real observations, not generated candles or optimizer cycle counts.
- Continue monitoring while the local service is running; do not promise unlimited uptime or an indefinitely running chat agent.
- Authentication failures, stale/missing quotes, closed markets, and invalid contract data must block new paper entries. These safeguards are not removed to satisfy a win-rate target.
- No public deployment is requested. Push the existing frontend and backend only after the user connects Git hosting and identifies the destination.

## Product

The imported Jarvis 2 dashboard displays portfolio, trade, and agent information from its FastAPI backend.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

_Populate as you build — sharp edges, "always run X before Y" rules._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
