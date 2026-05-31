"""Read-side helpers for computing account balances and trial balance."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ..models.accounting import Account, AccountType, LedgerEntry

ZERO = Decimal("0")


def account_balance(
    db: Session,
    account_id: UUID,
    as_of: date | None = None,
    start: date | None = None,
) -> Decimal:
    """Sum of `amount` in `ledger_entry` for the account, optionally bracketed."""
    stmt = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
        LedgerEntry.account_id == account_id
    )
    if start is not None:
        stmt = stmt.where(LedgerEntry.posting_date >= start)
    if as_of is not None:
        stmt = stmt.where(LedgerEntry.posting_date <= as_of)
    result = db.execute(stmt).scalar_one()
    return Decimal(result or 0)


def balances_by_account(
    db: Session,
    entity_id: UUID,
    as_of: date | None = None,
    start: date | None = None,
) -> dict[UUID, Decimal]:
    """Map of account_id -> signed amount (debit positive, credit negative)."""
    stmt = (
        select(LedgerEntry.account_id, func.sum(LedgerEntry.amount))
        .where(LedgerEntry.entity_id == entity_id)
        .group_by(LedgerEntry.account_id)
    )
    if start is not None:
        stmt = stmt.where(LedgerEntry.posting_date >= start)
    if as_of is not None:
        stmt = stmt.where(LedgerEntry.posting_date <= as_of)
    return {account_id: Decimal(amount or 0) for account_id, amount in db.execute(stmt)}


def trial_balance(
    db: Session, entity_id: UUID, as_of: date | None = None
) -> list[dict]:
    """List of rows ready for the trial balance report.

    Each row: {account_id, code, name, type, debit, credit}.
    Sign convention: assets/expenses positive on debit; liabilities/equity/revenue
    positive on credit.
    """
    sums = balances_by_account(db, entity_id, as_of=as_of)
    if not sums:
        return []

    accounts = db.execute(
        select(Account).where(
            and_(Account.entity_id == entity_id, Account.id.in_(sums.keys()))
        )
    ).scalars()

    rows: list[dict] = []
    for acct in accounts:
        amt = sums[acct.id]
        if amt > 0:
            debit, credit = amt, ZERO
        elif amt < 0:
            debit, credit = ZERO, -amt
        else:
            debit, credit = ZERO, ZERO
        rows.append(
            {
                "account_id": acct.id,
                "code": acct.code,
                "name": acct.name,
                "type": acct.type.value,
                "debit": debit,
                "credit": credit,
            }
        )
    rows.sort(key=lambda r: r["code"])
    return rows


def signed_balance_for_type(amount: Decimal, account_type: AccountType) -> Decimal:
    """Return the natural-sign balance for an account given a raw debit-positive sum.

    For ASSET/EXPENSE/CONTRA_LIABILITY/CONTRA_REVENUE, debit-positive == natural sign.
    For LIABILITY/EQUITY/REVENUE/CONTRA_ASSET, credit-positive == natural sign, so we
    flip.
    """
    debit_natural = account_type in {
        AccountType.ASSET,
        AccountType.EXPENSE,
        AccountType.CONTRA_LIABILITY,
        AccountType.CONTRA_REVENUE,
    }
    return amount if debit_natural else -amount
