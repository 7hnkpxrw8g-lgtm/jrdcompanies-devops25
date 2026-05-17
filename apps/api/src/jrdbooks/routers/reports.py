"""Financial reports: P&L, Balance Sheet, Trial Balance, Cash Flow, GL."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..accounting import balances_by_account, trial_balance
from ..accounting.balances import signed_balance_for_type
from ..db import get_db
from ..models.accounting import Account, AccountType, LedgerEntry
from ..schemas import (
    BalanceSheetResponse,
    BalanceSheetRow,
    PnLResponse,
    PnLRow,
    TrialBalanceRow,
)
from ..security import AuthContext, require_org

router = APIRouter(prefix="/reports", tags=["reports"])

ZERO = Decimal("0")


@router.get("/trial-balance", response_model=list[TrialBalanceRow])
def trial_balance_report(
    entity_id: UUID,
    as_of: date | None = None,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> list[TrialBalanceRow]:
    rows = trial_balance(db, entity_id, as_of=as_of)
    return [TrialBalanceRow(**r) for r in rows]


@router.get("/pnl", response_model=PnLResponse)
def pnl_report(
    entity_id: UUID,
    start: date,
    end: date,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> PnLResponse:
    sums = balances_by_account(db, entity_id, start=start, as_of=end)
    if not sums:
        return PnLResponse(
            entity_id=entity_id,
            start=start,
            end=end,
            revenue=[],
            expense=[],
            revenue_total=ZERO,
            expense_total=ZERO,
            net_income=ZERO,
        )
    accounts = db.execute(
        select(Account).where(
            and_(Account.entity_id == entity_id, Account.id.in_(sums.keys()))
        )
    ).scalars()

    revenue: list[PnLRow] = []
    expense: list[PnLRow] = []
    revenue_total = ZERO
    expense_total = ZERO
    for acct in accounts:
        natural = signed_balance_for_type(sums[acct.id], acct.type)
        if acct.type in {AccountType.REVENUE, AccountType.CONTRA_REVENUE}:
            revenue.append(
                PnLRow(account_id=acct.id, code=acct.code, name=acct.name, amount=natural)
            )
            revenue_total += natural
        elif acct.type == AccountType.EXPENSE:
            expense.append(
                PnLRow(account_id=acct.id, code=acct.code, name=acct.name, amount=natural)
            )
            expense_total += natural
    revenue.sort(key=lambda r: r.code)
    expense.sort(key=lambda r: r.code)
    return PnLResponse(
        entity_id=entity_id,
        start=start,
        end=end,
        revenue=revenue,
        expense=expense,
        revenue_total=revenue_total,
        expense_total=expense_total,
        net_income=revenue_total - expense_total,
    )


@router.get("/balance-sheet", response_model=BalanceSheetResponse)
def balance_sheet_report(
    entity_id: UUID,
    as_of: date,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> BalanceSheetResponse:
    sums = balances_by_account(db, entity_id, as_of=as_of)
    accounts = (
        db.execute(select(Account).where(Account.entity_id == entity_id)).scalars().all()
    )

    assets: list[BalanceSheetRow] = []
    liabilities: list[BalanceSheetRow] = []
    equity: list[BalanceSheetRow] = []
    assets_total = ZERO
    liabilities_total = ZERO
    equity_total = ZERO
    retained_earnings = ZERO

    for acct in accounts:
        amount = sums.get(acct.id, ZERO)
        if amount == 0:
            continue
        natural = signed_balance_for_type(amount, acct.type)
        row = BalanceSheetRow(
            account_id=acct.id, code=acct.code, name=acct.name, balance=natural
        )
        if acct.type in {AccountType.ASSET, AccountType.CONTRA_ASSET}:
            assets.append(row)
            assets_total += natural
        elif acct.type in {AccountType.LIABILITY, AccountType.CONTRA_LIABILITY}:
            liabilities.append(row)
            liabilities_total += natural
        elif acct.type == AccountType.EQUITY:
            equity.append(row)
            equity_total += natural
        elif acct.type in {AccountType.REVENUE, AccountType.CONTRA_REVENUE, AccountType.EXPENSE}:
            retained_earnings += signed_balance_for_type(amount, acct.type) * (
                -1 if acct.type == AccountType.EXPENSE else 1
            )

    assets.sort(key=lambda r: r.code)
    liabilities.sort(key=lambda r: r.code)
    equity.sort(key=lambda r: r.code)

    return BalanceSheetResponse(
        entity_id=entity_id,
        as_of=as_of,
        assets=assets,
        liabilities=liabilities,
        equity=equity,
        assets_total=assets_total,
        liabilities_total=liabilities_total,
        equity_total=equity_total + retained_earnings,
        retained_earnings=retained_earnings,
    )


@router.get("/general-ledger")
def general_ledger_report(
    entity_id: UUID,
    account_id: UUID | None = None,
    start: date | None = None,
    end: date | None = None,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> list[dict]:
    q = db.query(LedgerEntry).filter(LedgerEntry.entity_id == entity_id)
    if account_id:
        q = q.filter(LedgerEntry.account_id == account_id)
    if start:
        q = q.filter(LedgerEntry.posting_date >= start)
    if end:
        q = q.filter(LedgerEntry.posting_date <= end)
    rows = q.order_by(LedgerEntry.posting_date, LedgerEntry.id).all()

    account_codes = {
        a.id: (a.code, a.name)
        for a in db.execute(select(Account).where(Account.entity_id == entity_id)).scalars()
    }

    return [
        {
            "id": str(r.id),
            "journal_id": str(r.journal_id),
            "posting_date": r.posting_date.isoformat(),
            "account_id": str(r.account_id),
            "account_code": account_codes.get(r.account_id, ("", ""))[0],
            "account_name": account_codes.get(r.account_id, ("", ""))[1],
            "amount": float(r.amount),
            "debit": float(r.amount) if r.amount > 0 else 0.0,
            "credit": float(-r.amount) if r.amount < 0 else 0.0,
            "description": r.description,
        }
        for r in rows
    ]


@router.get("/ar-aging")
def ar_aging_report(
    entity_id: UUID,
    as_of: date | None = None,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> list[dict]:
    from datetime import date as _date

    from ..models.commerce import Customer, DocStatus, Invoice

    as_of = as_of or _date.today()
    buckets = {"current": ZERO, "1_30": ZERO, "31_60": ZERO, "61_90": ZERO, "over_90": ZERO}
    by_customer: dict[UUID, dict] = {}

    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.entity_id == entity_id,
            Invoice.status.in_([DocStatus.APPROVED, DocStatus.SENT, DocStatus.PARTIAL, DocStatus.OVERDUE]),
        )
        .all()
    )
    for inv in invoices:
        outstanding = inv.total - inv.amount_paid
        if outstanding <= 0:
            continue
        days = (as_of - inv.due_date).days
        if days <= 0:
            bucket = "current"
        elif days <= 30:
            bucket = "1_30"
        elif days <= 60:
            bucket = "31_60"
        elif days <= 90:
            bucket = "61_90"
        else:
            bucket = "over_90"
        buckets[bucket] += outstanding
        row = by_customer.setdefault(
            inv.customer_id,
            {
                "customer_id": inv.customer_id,
                "current": ZERO,
                "1_30": ZERO,
                "31_60": ZERO,
                "61_90": ZERO,
                "over_90": ZERO,
                "total": ZERO,
            },
        )
        row[bucket] += outstanding
        row["total"] += outstanding

    customers = {
        c.id: c.display_name
        for c in db.query(Customer).filter(Customer.id.in_(by_customer.keys())).all()
    }
    out = []
    for row in by_customer.values():
        out.append(
            {
                "customer_id": str(row["customer_id"]),
                "customer": customers.get(row["customer_id"], "—"),
                "current": float(row["current"]),
                "1_30": float(row["1_30"]),
                "31_60": float(row["31_60"]),
                "61_90": float(row["61_90"]),
                "over_90": float(row["over_90"]),
                "total": float(row["total"]),
            }
        )
    out.sort(key=lambda r: r["total"], reverse=True)
    return out
