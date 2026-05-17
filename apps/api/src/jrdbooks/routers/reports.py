"""Financial reports: P&L, Balance Sheet, Trial Balance, Cash Flow, GL."""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, select
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


@router.get("/ap-aging")
def ap_aging_report(
    entity_id: UUID,
    as_of: date | None = None,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Vendor-level aging buckets: current / 1-30 / 31-60 / 61-90 / 90+."""
    from datetime import date as _date

    from ..models.commerce import Bill, DocStatus, Vendor

    as_of = as_of or _date.today()
    by_vendor: dict[UUID, dict] = {}

    bills = (
        db.query(Bill)
        .filter(
            Bill.entity_id == entity_id,
            Bill.status.in_(
                [DocStatus.APPROVED, DocStatus.SENT, DocStatus.PARTIAL, DocStatus.OVERDUE]
            ),
        )
        .all()
    )
    for bill in bills:
        outstanding = bill.total - bill.amount_paid
        if outstanding <= 0:
            continue
        days = (as_of - bill.due_date).days
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
        row = by_vendor.setdefault(
            bill.vendor_id,
            {
                "vendor_id": bill.vendor_id,
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

    vendors = {
        v.id: v.display_name
        for v in db.query(Vendor).filter(Vendor.id.in_(by_vendor.keys())).all()
    }
    out = []
    for row in by_vendor.values():
        out.append(
            {
                "vendor_id": str(row["vendor_id"]),
                "vendor": vendors.get(row["vendor_id"], "—"),
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


@router.get("/cash-flow")
def cash_flow_report(
    entity_id: UUID,
    start: date,
    end: date,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> dict:
    """Indirect cash flow statement derived from the ledger.

    Operating = net income + non-cash adjustments (depreciation) + working capital changes.
    Investing / Financing buckets come from designated account flags.
    """
    sums = balances_by_account(db, entity_id, start=start, as_of=end)
    accounts = (
        db.execute(select(Account).where(Account.entity_id == entity_id)).scalars().all()
    )

    net_income = ZERO
    depreciation = ZERO
    operating_changes = ZERO
    investing = ZERO
    financing = ZERO
    beginning_cash = ZERO
    ending_cash = ZERO

    # P&L → net income
    for acct in accounts:
        amt = sums.get(acct.id, ZERO)
        if amt == 0:
            continue
        natural = signed_balance_for_type(amt, acct.type)
        if acct.type in {AccountType.REVENUE, AccountType.CONTRA_REVENUE}:
            net_income += natural
        elif acct.type == AccountType.EXPENSE:
            net_income -= natural
            if "depreciation" in acct.name.lower():
                depreciation += natural

    # Cash position deltas
    cash_acct_ids = [a.id for a in accounts if a.is_bank or a.is_cash]
    for acct_id in cash_acct_ids:
        beginning_cash += account_balance_helper(db, acct_id, end=start)
        ending_cash += account_balance_helper(db, acct_id, end=end)

    # Working capital: AR + AP changes
    for acct in accounts:
        if acct.is_ar:
            delta = sums.get(acct.id, ZERO)
            operating_changes -= delta  # AR ↑ reduces cash
        elif acct.is_ap:
            delta = sums.get(acct.id, ZERO)
            operating_changes -= delta  # AP ↑ increases cash → -(-) = +

    # Investing: changes in fixed-asset accounts (non-bank, non-cash assets)
    for acct in accounts:
        if acct.type == AccountType.ASSET and not (acct.is_bank or acct.is_cash or acct.is_ar):
            investing -= sums.get(acct.id, ZERO)
        elif acct.type == AccountType.CONTRA_ASSET:
            investing += sums.get(acct.id, ZERO)

    # Financing: equity contributions/distributions, notes payable changes
    for acct in accounts:
        if acct.type == AccountType.EQUITY or (
            acct.type == AccountType.LIABILITY
            and "note" in acct.name.lower()
        ):
            financing -= sums.get(acct.id, ZERO)

    operating_total = net_income + depreciation + operating_changes
    net_change = operating_total + investing + financing

    return {
        "entity_id": str(entity_id),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "operating": {
            "net_income": float(net_income),
            "depreciation": float(depreciation),
            "working_capital_changes": float(operating_changes),
            "total": float(operating_total),
        },
        "investing": {"total": float(investing)},
        "financing": {"total": float(financing)},
        "net_change_in_cash": float(net_change),
        "beginning_cash": float(beginning_cash),
        "ending_cash": float(ending_cash),
        "reconciliation_delta": float(ending_cash - beginning_cash - net_change),
    }


def account_balance_helper(db: Session, account_id: UUID, end: date) -> Decimal:
    """Lightweight balance lookup used by cash-flow."""
    stmt = (
        select(func.coalesce(func.sum(LedgerEntry.amount), 0))
        .where(LedgerEntry.account_id == account_id)
        .where(LedgerEntry.posting_date < end)
    )
    return Decimal(db.execute(stmt).scalar_one() or 0)


@router.get("/inventory-valuation")
def inventory_valuation_report(
    entity_id: UUID,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> list[dict]:
    from ..models.inventory import InventoryItem

    items = (
        db.query(InventoryItem)
        .filter(InventoryItem.entity_id == entity_id, InventoryItem.is_active.is_(True))
        .order_by(InventoryItem.sku)
        .all()
    )
    return [
        {
            "item_id": str(it.id),
            "sku": it.sku,
            "name": it.name,
            "on_hand": float(it.on_hand),
            "avg_cost": float(it.avg_cost),
            "value": float(it.on_hand * it.avg_cost),
            "below_reorder": it.on_hand < it.reorder_point,
        }
        for it in items
    ]


@router.get("/fuel-variance")
def fuel_variance_report(
    entity_id: UUID,
    start: date | None = None,
    end: date | None = None,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> dict:
    from ..models.fuel_ops import FuelDispense, FuelTank

    tanks = (
        db.query(FuelTank)
        .filter(FuelTank.entity_id == entity_id, FuelTank.is_active.is_(True))
        .all()
    )
    out_tanks = []
    grand_variance_gal = ZERO
    grand_variance_value = ZERO
    for tank in tanks:
        q = db.query(FuelDispense).filter(FuelDispense.tank_id == tank.id)
        if start:
            q = q.filter(FuelDispense.dispense_date >= start)
        if end:
            q = q.filter(FuelDispense.dispense_date <= end)
        dispenses = q.all()
        total_gal_sold = sum((d.gallons_sold for d in dispenses), ZERO)
        total_variance_gal = sum((d.variance_gallons for d in dispenses), ZERO)
        total_variance_val = sum((d.variance_value for d in dispenses), ZERO)
        grand_variance_gal += total_variance_gal
        grand_variance_value += total_variance_val
        out_tanks.append(
            {
                "tank_id": str(tank.id),
                "name": tank.name,
                "fuel_type": tank.fuel_type,
                "gallons_sold": float(total_gal_sold),
                "variance_gallons": float(total_variance_gal),
                "variance_value": float(total_variance_val),
                "pct_variance": (
                    float(total_variance_gal / total_gal_sold * 100)
                    if total_gal_sold > 0
                    else 0.0
                ),
            }
        )
    return {
        "entity_id": str(entity_id),
        "start": start.isoformat() if start else None,
        "end": end.isoformat() if end else None,
        "tanks": out_tanks,
        "totals": {
            "variance_gallons": float(grand_variance_gal),
            "variance_value": float(grand_variance_value),
        },
    }


# ---------- Exports ----------


def _csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    if not rows:
        rows = [{"_empty": "no data"}]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/trial-balance.csv")
def trial_balance_csv(
    entity_id: UUID,
    as_of: date | None = None,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    rows = trial_balance(db, entity_id, as_of=as_of)
    flat = [
        {
            "code": r["code"],
            "name": r["name"],
            "type": r["type"],
            "debit": float(r["debit"]),
            "credit": float(r["credit"]),
        }
        for r in rows
    ]
    return _csv_response(flat, f"trial-balance-{(as_of or date.today()).isoformat()}.csv")


@router.get("/general-ledger.csv")
def general_ledger_csv(
    entity_id: UUID,
    start: date | None = None,
    end: date | None = None,
    account_id: UUID | None = Query(default=None),
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    rows = general_ledger_report(
        entity_id=entity_id, account_id=account_id, start=start, end=end, ctx=ctx, db=db
    )
    flat = [
        {
            "posting_date": r["posting_date"],
            "account_code": r["account_code"],
            "account_name": r["account_name"],
            "debit": r["debit"],
            "credit": r["credit"],
            "description": r["description"] or "",
            "journal_id": r["journal_id"],
        }
        for r in rows
    ]
    return _csv_response(flat, f"general-ledger-{(end or date.today()).isoformat()}.csv")
