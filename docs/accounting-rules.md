# Accounting rules

The JRDbooks ledger enforces a small number of hard invariants. The code is
designed so violating them is impossible from the API, and difficult even from
direct DB access.

## 1. Double-entry, always

Every `journal` has at least two `journal_line` rows. For each posted journal,
`sum(debit) == sum(credit) > 0`. This is enforced in three layers:

- Python posting engine (`jrdbooks/accounting/posting.py::_ensure_balanced`)
- DB check constraint `journal_line.debit_xor_credit` — exactly one of debit /
  credit is positive on each line.
- DB check constraint `ledger_entry.amount_nonzero` — no zero ledger rows.

## 2. Posted journals are immutable

`ledger_entry` is append-only. Once a journal moves from `draft` to `posted`,
its lines are frozen — corrections happen via `reverse_journal`, which creates
a brand-new journal with the debits and credits swapped. The original journal
moves to status `reversed` and gets `reversed_by_id` set.

## 3. Sign convention

`ledger_entry.amount` is a signed value:
- `> 0` = debit
- `< 0` = credit
- per journal, the rows sum to zero

For reporting, `signed_balance_for_type` flips the sign for accounts whose
natural side is the credit side (liability, equity, revenue, contra-asset).

## 4. Period closes lock the books

`period_close` records a finished fiscal period. The posting engine refuses to
post any journal whose `posting_date` falls inside a closed period. Closing
also writes a retained-earnings journal that zeros out revenue and expense
accounts into equity.

## 5. Multi-currency

- `journal.currency` + `journal.fx_rate` define the FX context.
- `ledger_entry.amount` stays in the journal currency; `ledger_entry.fx_amount`
  is the base-currency equivalent computed at posting time.
- Reports query `fx_amount` for consolidated views.

## 6. Multi-entity

Every accounting row carries `org_id` and `entity_id`. Reports require an
`entity_id` filter (or a consolidation view that explicitly unions entities
marked `is_consolidation_target = true`). Inter-entity transactions post two
journals — one per entity — linked via `source_ref`.

## 7. Audit trail

Every state change writes an `audit_event` row containing:

- `actor_user_id` (or `actor_label` for system actions)
- `source` (`api`, `system`, `integration`)
- `action` (`journal.post`, `invoice.create`, etc.)
- `target_kind`, `target_id`
- `request_id` so HTTP logs join cleanly
- `before` / `after` JSON snapshots for non-trivial diffs

Audit rows are never updated. They are deleted only as part of an
organization-level data purge.
