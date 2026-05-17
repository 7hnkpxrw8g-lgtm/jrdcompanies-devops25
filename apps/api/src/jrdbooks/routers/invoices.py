"""Invoice creation, listing, posting (book AR + revenue)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from ..accounting import PostingError, post_journal
from ..db import get_db
from ..models.accounting import Account, Journal, JournalLine, JournalSource
from ..models.audit import AuditEvent
from ..models.commerce import Customer, DocStatus, Invoice, InvoiceLine, LineItemKind
from ..models.core import Entity
from ..schemas import InvoiceCreate, InvoiceOut
from ..security import AuthContext, require_org

router = APIRouter(prefix="/invoices", tags=["invoices"])

ZERO = Decimal("0")


def _next_invoice_no(db: Session, org_id: UUID) -> str:
    n = db.query(Invoice).filter(Invoice.org_id == org_id).count() + 1
    return f"INV-{n:06d}"


def _ar_account(db: Session, entity_id: UUID) -> Account:
    acct = (
        db.query(Account)
        .filter(Account.entity_id == entity_id, Account.is_ar.is_(True))
        .first()
    )
    if acct is None:
        raise HTTPException(
            status_code=400, detail="Entity is missing an A/R account (is_ar=true)"
        )
    return acct


def _tax_payable_account(db: Session, entity_id: UUID) -> Account | None:
    return (
        db.query(Account)
        .filter(Account.entity_id == entity_id, Account.code == "2100")
        .first()
    )


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    entity_id: UUID | None = None,
    customer_id: UUID | None = None,
    status: str | None = None,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> list[InvoiceOut]:
    q = (
        db.query(Invoice)
        .options(selectinload(Invoice.lines))
        .filter(Invoice.org_id == ctx.org_id)
    )
    if entity_id:
        q = q.filter(Invoice.entity_id == entity_id)
    if customer_id:
        q = q.filter(Invoice.customer_id == customer_id)
    if status:
        q = q.filter(Invoice.status == status)
    q = q.order_by(Invoice.issue_date.desc(), Invoice.invoice_no.desc()).limit(500)
    return [InvoiceOut.model_validate(r) for r in q.all()]


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: UUID,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> InvoiceOut:
    inv = (
        db.query(Invoice)
        .options(selectinload(Invoice.lines))
        .filter(Invoice.id == invoice_id, Invoice.org_id == ctx.org_id)
        .one_or_none()
    )
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return InvoiceOut.model_validate(inv)


@router.post("", response_model=InvoiceOut, status_code=201)
def create_invoice(
    payload: InvoiceCreate,
    approve: bool = False,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> InvoiceOut:
    entity = db.get(Entity, payload.entity_id)
    if entity is None or entity.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Entity not found")
    customer = db.get(Customer, payload.customer_id)
    if customer is None or customer.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Customer not found")

    if not payload.lines:
        raise HTTPException(status_code=400, detail="Invoice must have lines")

    inv = Invoice(
        org_id=ctx.org_id,
        entity_id=entity.id,
        customer_id=customer.id,
        invoice_no=payload.invoice_no or _next_invoice_no(db, ctx.org_id),
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        currency=payload.currency,
        notes=payload.notes,
        status=DocStatus.DRAFT,
    )

    subtotal = ZERO
    tax_total = ZERO
    discount_total = ZERO

    for line in payload.lines:
        line_subtotal = (line.quantity * line.unit_price).quantize(Decimal("0.0001"))
        line_after_discount = line_subtotal - line.discount_amount
        line_tax = (line_after_discount * line.tax_rate).quantize(Decimal("0.0001"))
        line_total = line_after_discount + line_tax
        subtotal += line_subtotal
        tax_total += line_tax
        discount_total += line.discount_amount
        inv.lines.append(
            InvoiceLine(
                line_no=line.line_no,
                kind=LineItemKind(line.kind),
                revenue_account_id=line.revenue_account_id,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rate=line.tax_rate,
                discount_amount=line.discount_amount,
                line_total=line_total,
            )
        )
    inv.subtotal = subtotal
    inv.tax_total = tax_total
    inv.discount_total = discount_total
    inv.total = subtotal - discount_total + tax_total

    db.add(inv)
    db.flush()

    if approve:
        _post_invoice_journal(db, inv, ctx)

    db.add(
        AuditEvent(
            org_id=ctx.org_id,
            entity_id=entity.id,
            actor_user_id=ctx.user.id,
            source="api",
            action="invoice.create",
            target_kind="invoice",
            target_id=inv.id,
            after={"invoice_no": inv.invoice_no, "total": float(inv.total)},
        )
    )

    db.commit()
    db.refresh(inv)
    return InvoiceOut.model_validate(inv)


def _post_invoice_journal(db: Session, inv: Invoice, ctx: AuthContext) -> None:
    ar = _ar_account(db, inv.entity_id)
    tax_acct = _tax_payable_account(db, inv.entity_id)

    journal = Journal(
        org_id=inv.org_id,
        entity_id=inv.entity_id,
        journal_no=f"INV-{inv.invoice_no}",
        posting_date=inv.issue_date,
        memo=f"Invoice {inv.invoice_no}",
        source=JournalSource.INVOICE,
        source_ref=str(inv.id),
        currency=inv.currency,
    )
    db.add(journal)
    db.flush()

    db.add(
        JournalLine(
            journal_id=journal.id,
            line_no=1,
            account_id=ar.id,
            debit=inv.total,
            credit=ZERO,
            description=f"Invoice {inv.invoice_no}",
            customer_id=inv.customer_id,
        )
    )
    line_no = 2
    for ln in inv.lines:
        net_revenue = (ln.quantity * ln.unit_price - ln.discount_amount).quantize(
            Decimal("0.0001")
        )
        db.add(
            JournalLine(
                journal_id=journal.id,
                line_no=line_no,
                account_id=ln.revenue_account_id,
                debit=ZERO,
                credit=net_revenue,
                description=ln.description,
                customer_id=inv.customer_id,
            )
        )
        line_no += 1
    if inv.tax_total > ZERO:
        if tax_acct is None:
            raise HTTPException(
                status_code=400,
                detail="Invoice has tax but no Tax Payable account (code 2100) exists",
            )
        db.add(
            JournalLine(
                journal_id=journal.id,
                line_no=line_no,
                account_id=tax_acct.id,
                debit=ZERO,
                credit=inv.tax_total,
                description="Sales tax payable",
            )
        )
    db.flush()
    db.refresh(journal)

    try:
        post_journal(db, journal.id, actor_user_id=ctx.user.id)
    except PostingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    inv.journal_id = journal.id
    inv.status = DocStatus.APPROVED
