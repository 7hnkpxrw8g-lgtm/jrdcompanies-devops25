"""Dashboard aggregator endpoint."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.accounting import Account, AccountType
from ..models.banking import BankAccount, BankTransaction, BankTxStatus
from ..models.commerce import Bill, DocStatus, Invoice
from ..security import AuthContext, require_org
from .reports import pnl_report

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

ZERO = Decimal("0")


@router.get("/summary")
def dashboard_summary(
    entity_id: UUID,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> dict:
    today = date.today()
    start_month = today.replace(day=1)

    pnl = pnl_report(
        entity_id=entity_id, start=start_month, end=today, ctx=ctx, db=db
    )

    cash_balance = ZERO
    bank_accounts = (
        db.query(BankAccount)
        .filter(BankAccount.org_id == ctx.org_id, BankAccount.entity_id == entity_id)
        .all()
    )
    for ba in bank_accounts:
        cash_balance += ba.last_balance

    unreconciled = (
        db.query(BankTransaction)
        .filter(
            BankTransaction.org_id == ctx.org_id,
            BankTransaction.entity_id == entity_id,
            BankTransaction.status == BankTxStatus.UNRECONCILED,
        )
        .count()
    )

    ar_outstanding = db.execute(
        select(func.coalesce(func.sum(Invoice.total - Invoice.amount_paid), 0))
        .where(Invoice.entity_id == entity_id)
        .where(
            Invoice.status.in_(
                [DocStatus.APPROVED, DocStatus.SENT, DocStatus.PARTIAL, DocStatus.OVERDUE]
            )
        )
    ).scalar_one() or 0

    ap_outstanding = db.execute(
        select(func.coalesce(func.sum(Bill.total - Bill.amount_paid), 0))
        .where(Bill.entity_id == entity_id)
        .where(
            Bill.status.in_(
                [DocStatus.APPROVED, DocStatus.SENT, DocStatus.PARTIAL, DocStatus.OVERDUE]
            )
        )
    ).scalar_one() or 0

    revenue_trend: list[dict] = []
    for offset in range(5, -1, -1):
        m_start = (today.replace(day=1) - timedelta(days=offset * 30)).replace(day=1)
        if offset == 0:
            m_end = today
        else:
            next_first = (m_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            m_end = next_first - timedelta(days=1)
        pnl_m = pnl_report(entity_id=entity_id, start=m_start, end=m_end, ctx=ctx, db=db)
        revenue_trend.append(
            {
                "month": m_start.strftime("%b %Y"),
                "revenue": float(pnl_m.revenue_total),
                "expense": float(pnl_m.expense_total),
                "net_income": float(pnl_m.net_income),
            }
        )

    return {
        "cash_balance": float(cash_balance),
        "month_to_date": {
            "revenue": float(pnl.revenue_total),
            "expense": float(pnl.expense_total),
            "net_income": float(pnl.net_income),
        },
        "unreconciled_count": unreconciled,
        "ar_outstanding": float(ar_outstanding),
        "ap_outstanding": float(ap_outstanding),
        "bank_accounts": [
            {
                "id": str(ba.id),
                "name": ba.name,
                "balance": float(ba.last_balance),
                "currency": ba.currency,
            }
            for ba in bank_accounts
        ],
        "revenue_trend": revenue_trend,
    }
