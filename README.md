# JRDbooks

A modern, multi-entity accounting platform built like a world-class fintech ERP.

JRDbooks combines double-entry accounting, multi-entity consolidation, real-time
bank reconciliation, fuel operations, repair-order tracking, AI-assisted
categorization, and audit-grade observability in a single platform.

## What's inside

| Path | Purpose |
| --- | --- |
| `apps/api` | FastAPI service: double-entry ledger, posting engine, reporting, integrations |
| `apps/web` | Next.js App Router UI: dashboard, ledger, transactions, reports, integrations |
| `infra/` | Docker Compose stack, deployment configs, observability |
| `docs/` | Architecture notes, accounting rules, integration playbooks |
| `tests/` | End-to-end Playwright suites and API contract tests |

## Core principles

1. **Double-entry, always.** Every posted journal balances. No row in `ledger_entry`
   is ever mutated after posting — reversals are recorded as new offsetting entries.
2. **Multi-entity from day one.** Every accounting row carries `org_id` and
   `entity_id`. Consolidation is a query, not a migration.
3. **Audit-grade.** Every state change writes an `audit_event` with actor, source,
   before/after, and request_id. Financial history is append-only.
4. **Browser-tested.** Features ship with Playwright coverage of the golden path.
5. **Observable.** Structured logs, OpenTelemetry traces, Sentry, request IDs, and
   health checks are first-class.

## Quick start

```bash
# 1. Boot the stack (Postgres, Redis, API, Web)
docker compose -f infra/docker-compose.yml up --build

# 2. In another shell, run migrations and seed a demo org
docker compose -f infra/docker-compose.yml exec api alembic upgrade head
docker compose -f infra/docker-compose.yml exec api python -m jrdbooks.seed

# 3. Open the app
open http://localhost:3000
```

Demo credentials: `demo@jrdbooks.io` / `demo`.

## Local development (no Docker)

```bash
# Backend
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
export DATABASE_URL=postgresql+psycopg://jrd:jrd@localhost:5432/jrdbooks
alembic upgrade head
uvicorn jrdbooks.main:app --reload --port 8000

# Frontend (separate shell)
cd apps/web
pnpm install
pnpm dev
```

## Accounting rules

See [`docs/accounting-rules.md`](docs/accounting-rules.md) for the full posting
contract. Highlights:

- Debits must equal credits for every journal.
- Posted journals are immutable. Corrections are reversing journals.
- Closing entries write to `period_close` and lock the period.
- All money is stored as `numeric(18,4)` with explicit ISO 4217 currency codes.
- FX conversion uses the rate effective on the journal `posting_date`.

## Reports

| Report | Endpoint | UI |
| --- | --- | --- |
| Profit & Loss | `GET /reports/pnl` | `/reports/pnl` |
| Balance Sheet | `GET /reports/balance-sheet` | `/reports/balance-sheet` |
| Cash Flow | `GET /reports/cash-flow` | `/reports/cash-flow` |
| Trial Balance | `GET /reports/trial-balance` | `/reports/trial-balance` |
| General Ledger | `GET /reports/general-ledger` | `/reports/general-ledger` |
| AR Aging | `GET /reports/ar-aging` | `/reports/ar-aging` |
| AP Aging | `GET /reports/ap-aging` | `/reports/ap-aging` |
| Fuel Variance | `GET /reports/fuel-variance` | `/reports/fuel-variance` |
| Inventory Valuation | `GET /reports/inventory-valuation` | `/reports/inventory` |

Every report supports `?entity_id=`, `?start=`, `?end=`, and `?format=pdf|xlsx|csv`.

## Verification

The platform is verified end-to-end via:

- `pytest` for backend (`apps/api/tests/`)
- `vitest` for frontend units (`apps/web/src/__tests__/`)
- `playwright` for browser flows (`tests/e2e/`)
- `make smoke` for a curl-driven contract check against a running stack

See [`docs/qa.md`](docs/qa.md) for the full QA loop.
