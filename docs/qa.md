# QA loop

JRDbooks ships behind three layers of automated verification.

## Layer 1: posting invariants (`apps/api/tests/test_posting.py`)

Pure-Python tests of the accounting engine, runnable in milliseconds against
an in-memory SQLite. These guard the core invariants:

- Balanced journals post; unbalanced ones raise `PostingError`.
- Idempotent — posting a posted journal does nothing.
- Reversal creates an offsetting journal and marks the original `reversed`.
- Posting to a closed period is rejected.
- Trial balance ties.
- DB check constraints reject malformed rows.

## Layer 2: API contract (`apps/api/tests/test_api.py`)

Boot the FastAPI app against an in-memory SQLite, seed the demo org, log in,
walk through the critical endpoints:

- `/auth/token` returns a JWT
- `/entities` lists both seeded entities
- `/accounts` returns the seeded COA (36 accounts × 2 entities)
- `/journals` create + auto-post + reverse
- `/reports/trial-balance` sums to zero
- `/reports/balance-sheet` satisfies `A = L + E`
- `/dashboard/summary` returns the full payload shape
- `/banking/transactions/{id}/categorize` posts a journal

Run with `pytest -q` from `apps/api/`.

## Layer 3: browser flows (`tests/e2e/`)

Playwright spec runs against the docker-compose stack:

1. Open `/login`, sign in as `demo@jrdbooks.io`
2. Land on `/app` (dashboard); assert cash balance and bank cards render
3. Open `/app/transactions/new`, fill a balanced journal, click Post
4. Open `/app/ledger`; assert the new journal lines appear
5. Open `/app/reports?r=trial-balance`; assert "In balance" badge
6. Open `/app/reconciliation`; categorize one transaction; assert it leaves
   the queue and a new journal exists

Screenshots are saved under `playwright-report/` for review.

## Manual smoke (`make smoke`)

A curl-driven script runs after a fresh `docker compose up`:

```
make smoke
```

This drives the same five flows the e2e suite covers, but using only `curl` —
ideal for verifying production-like deployments.
