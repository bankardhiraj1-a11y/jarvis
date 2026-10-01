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
3. Preserve the created dashboard design and behavior. The user explicitly authorized currency formatting and a Charges tab; these are narrow exceptions, not permission for a general redesign.
4. Paper-capital allocation may be calculated automatically in pursuit of the performance target. Never allocate real funds, place real orders, hide losing trades, or manipulate the denominator to meet the target.
5. Develop an evidence-based self-learning process for this platform. Synthetic test fixtures may test software but must never enter trade history or performance claims.
6. Retain all trade data, including losses, for month-end analysis. Do not prune, reset, or rewrite history. Full-history snapshots and month-filtered exports must include provider provenance and distinguish legacy/unverified records. Local snapshots are not offsite disaster recovery.

## Evidence and runtime constraints

- Real market prices only for recorded paper trades. No sample/fake trades or estimated option premiums presented as live.
- Report verified closed-trade sample sizes, net P&L and losses alongside win rate. A claimed target requires sufficient real observations, not generated candles or optimizer cycle counts.
- Continue monitoring while the local service is running; do not promise unlimited uptime or an indefinitely running chat agent.
- Authentication failures, stale/missing quotes, closed markets, and invalid contract data must block new paper entries. These safeguards are not removed to satisfy a win-rate target.
- No public deployment is requested. Push the existing frontend and backend only after the user connects Git hosting and identifies the destination.

## Authorized paper-learning policy

- The user authorized autonomous experimental paper decisions on 2026-10-01. Gold and Sensex options scalping may collect forward paper outcomes without per-entry permission; this is not approval for real broker orders or a claim of validated profitability.
- Options and Sensex options scalping are intraday only. Attempt quote-backed exits before the Indian market closes; missing fresh quotes must leave an explicit overdue/pending exit, never a fabricated same-day fill.
- Gold holds must be justified by the strategy. Default to bounded intraday holding and avoid New York financing rollover while applicable financing remains unknown. Overnight permission requires explicit strategy intent and verified costs.
- Stocks may hold according to the strategy. Quantity must fit available capital and risk limits, and expected target profit must remain positive after estimated charges. Reject unverifiable costs or economically inadequate setups rather than increasing quantity without limits.
- Indian charge estimates use the requested Zerodha reference, not a claim that Dhan invoices have been verified. Keep OANDA spread already embedded in executable-side P&L separate from additional commission/financing; unknown fees must not become zero.
- Keep automatic reviews and learning experimental until genuine forward samples support validation. Monitoring depends on a running service and valid market data; holidays and inactive entry windows must never be filled with artificial trades.

## Product

The imported Jarvis 2 dashboard displays portfolio, trade, and agent information from its FastAPI backend.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

_Populate as you build — sharp edges, "always run X before Y" rules._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
