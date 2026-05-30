"""Bills + bill approval + AP/expense journal posting."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..accounting import PostingError, post_journal
from ..db import get_db
from ..models.accounting import Account, Journal, JournalLine, JournalSource
from ..models.audit import AuditEvent
from ..models.commerce import Bill, DocStatus, Vendor
from ..models.core import Entity
from ..security import AuthContext, require_org

router = APIRouter(prefix="/bills", tags=["bills"])

ZERO = Decimal("0")


def _next_bill_no(db: Session, org_id: UUID) -> str:
    n = db.query(Bill).filter(Bill.org_id == org_id).count() + 1
    return f"BILL-{n:06d}"


def _ap_account(db: Session, entity_id: UUID) -> Account:
    acct = (
        db.query(Account)
        .filter(Account.entity_id == entity_id, Account.is_ap.is_(True))
        .first()
    )
    if acct is None:
        raise HTTPException(
            status_code=400, detail="Entity is missing an A/P account (is_ap=true)"
        )
    return acct


class BillLineIn(BaseModel):
    line_no: int = Field(ge=1)
    expense_account_id: UUID
    description: str
    amount: Decimal


class BillCreate(BaseModel):
    entity_id: UUID
    vendor_id: UUID
    bill_no: str | None = None
    issue_date: date
    due_date: date
    currency: str = "USD"
    notes: str | None = None
    lines: list[BillLineIn]


class BillOut(BaseModel):
    id: UUID
    bill_no: str
    vendor_id: UUID
    issue_date: date
    due_date: date
    status: str
    currency: str
    total: Decimal
    amount_paid: Decimal
    approval_status: str


@router.get("", response_model=list[BillOut])
def list_bills(
    entity_id: UUID | None = None,
    vendor_id: UUID | None = None,
    status: str | None = None,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> list[BillOut]:
    q = db.query(Bill).filter(Bill.org_id == ctx.org_id)
    if entity_id:
        q = q.filter(Bill.entity_id == entity_id)
    if vendor_id:
        q = q.filter(Bill.vendor_id == vendor_id)
    if status:
        q = q.filter(Bill.status == status)
    q = q.order_by(Bill.issue_date.desc(), Bill.bill_no.desc()).limit(500)
    return [
        BillOut(
            id=b.id,
            bill_no=b.bill_no,
            vendor_id=b.vendor_id,
            issue_date=b.issue_date,
            due_date=b.due_date,
            status=b.status.value,
            currency=b.currency,
            total=b.total,
            amount_paid=b.amount_paid,
            approval_status=b.approval_status,
        )
        for b in q.all()
    ]


@router.post("", response_model=BillOut, status_code=201)
def create_bill(
    payload: BillCreate,
    approve: bool = False,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> BillOut:
    entity = db.get(Entity, payload.entity_id)
    if entity is None or entity.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Entity not found")
    vendor = db.get(Vendor, payload.vendor_id)
    if vendor is None or vendor.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if not payload.lines:
        raise HTTPException(status_code=400, detail="Bill must have lines")

    total = sum((ln.amount for ln in payload.lines), ZERO)
    bill = Bill(
        org_id=ctx.org_id,
        entity_id=entity.id,
        vendor_id=vendor.id,
        bill_no=payload.bill_no or _next_bill_no(db, ctx.org_id),
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        currency=payload.currency,
        notes=payload.notes,
        status=DocStatus.DRAFT,
        subtotal=total,
        total=total,
    )
    db.add(bill)
    db.flush()

    if approve:
        _post_bill_journal(db, bill, payload.lines, ctx)
        bill.approval_status = "approved"
        bill.approved_by = ctx.user.id
        bill.status = DocStatus.APPROVED

    db.add(
        AuditEvent(
            org_id=ctx.org_id,
            entity_id=entity.id,
            actor_user_id=ctx.user.id,
            source="api",
            action="bill.create",
            target_kind="bill",
            target_id=bill.id,
            after={
                "bill_no": bill.bill_no,
                "vendor_id": str(vendor.id),
                "total": float(total),
                "approved": approve,
            },
        )
    )
    db.commit()
    db.refresh(bill)
    return BillOut(
        id=bill.id,
        bill_no=bill.bill_no,
        vendor_id=bill.vendor_id,
        issue_date=bill.issue_date,
        due_date=bill.due_date,
        status=bill.status.value,
        currency=bill.currency,
        total=bill.total,
        amount_paid=bill.amount_paid,
        approval_status=bill.approval_status,
    )


def _post_bill_journal(
    db: Session, bill: Bill, lines: list[BillLineIn], ctx: AuthContext
) -> None:
    ap = _ap_account(db, bill.entity_id)
    journal = Journal(
        org_id=bill.org_id,
        entity_id=bill.entity_id,
        journal_no=f"BILL-{bill.bill_no}",
        posting_date=bill.issue_date,
        memo=f"Bill {bill.bill_no}",
        source=JournalSource.BILL,
        source_ref=str(bill.id),
        currency=bill.currency,
    )
    db.add(journal)
    db.flush()

    line_no = 1
    for ln in lines:
        db.add(
            JournalLine(
                journal_id=journal.id,
                line_no=line_no,
                account_id=ln.expense_account_id,
                debit=ln.amount,
                credit=ZERO,
                description=ln.description,
                vendor_id=bill.vendor_id,
            )
        )
        line_no += 1
    db.add(
        JournalLine(
            journal_id=journal.id,
            line_no=line_no,
            account_id=ap.id,
            debit=ZERO,
            credit=bill.total,
            description=f"Bill {bill.bill_no}",
            vendor_id=bill.vendor_id,
        )
    )
    db.flush()
    db.refresh(journal)
    try:
        post_journal(db, journal.id, actor_user_id=ctx.user.id)
    except PostingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    bill.journal_id = journal.id


@router.post("/{bill_id}/approve", response_model=BillOut)
def approve_bill(
    bill_id: UUID,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> BillOut:
    bill = db.get(Bill, bill_id)
    if bill is None or bill.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Bill not found")
    if bill.approval_status == "approved":
        raise HTTPException(status_code=400, detail="Already approved")
    # We need the original line items to post the journal. For simplicity,
    # we lift them from the journal_id linkage. If none exists, we cannot
    # approve without re-supplying lines — block in that case.
    if bill.journal_id is not None:
        raise HTTPException(status_code=400, detail="Bill already has a journal")
    raise HTTPException(
        status_code=400,
        detail="Approving a previously-saved draft via this endpoint isn't supported yet; "
        "create the bill with ?approve=true instead.",
    )
