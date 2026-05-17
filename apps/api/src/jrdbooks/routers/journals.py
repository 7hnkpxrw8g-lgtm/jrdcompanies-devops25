"""Journal entries: create draft, post, reverse, list."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from ..accounting import PostingError, post_journal, reverse_journal
from ..db import get_db
from ..models.accounting import Account, Journal, JournalLine, JournalStatus
from ..models.audit import AuditEvent
from ..models.core import Entity
from ..schemas import JournalCreate, JournalOut
from ..security import AuthContext, require_org

router = APIRouter(prefix="/journals", tags=["journals"])


def _next_journal_no(db: Session, entity_id: UUID) -> str:
    n = db.query(Journal).filter(Journal.entity_id == entity_id).count() + 1
    return f"JE-{n:06d}"


@router.get("", response_model=list[JournalOut])
def list_journals(
    entity_id: UUID,
    status: JournalStatus | None = None,
    start: date | None = None,
    end: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> list[JournalOut]:
    q = (
        db.query(Journal)
        .options(selectinload(Journal.lines))
        .filter(Journal.org_id == ctx.org_id, Journal.entity_id == entity_id)
    )
    if status:
        q = q.filter(Journal.status == status)
    if start:
        q = q.filter(Journal.posting_date >= start)
    if end:
        q = q.filter(Journal.posting_date <= end)
    q = q.order_by(Journal.posting_date.desc(), Journal.journal_no.desc()).limit(limit)
    return [JournalOut.model_validate(j) for j in q.all()]


@router.get("/{journal_id}", response_model=JournalOut)
def get_journal(
    journal_id: UUID,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> JournalOut:
    j = (
        db.query(Journal)
        .options(selectinload(Journal.lines))
        .filter(Journal.id == journal_id, Journal.org_id == ctx.org_id)
        .one_or_none()
    )
    if j is None:
        raise HTTPException(status_code=404, detail="Journal not found")
    return JournalOut.model_validate(j)


@router.post("", response_model=JournalOut, status_code=201)
def create_journal(
    payload: JournalCreate,
    post: bool = Query(default=False, description="Post immediately after creating"),
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> JournalOut:
    entity = db.get(Entity, payload.entity_id)
    if entity is None or entity.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Entity not found")

    if not payload.lines:
        raise HTTPException(status_code=400, detail="Journal must have lines")

    # Validate all accounts belong to entity
    account_ids = {ln.account_id for ln in payload.lines}
    accounts = (
        db.query(Account)
        .filter(Account.id.in_(account_ids), Account.entity_id == entity.id)
        .all()
    )
    if len(accounts) != len(account_ids):
        raise HTTPException(
            status_code=400, detail="One or more accounts are not in this entity"
        )

    journal = Journal(
        org_id=ctx.org_id,
        entity_id=entity.id,
        journal_no=payload.journal_no or _next_journal_no(db, entity.id),
        posting_date=payload.posting_date,
        memo=payload.memo,
        source=payload.source,
        source_ref=payload.source_ref,
        currency=payload.currency,
        fx_rate=payload.fx_rate,
    )
    db.add(journal)
    db.flush()

    for line in payload.lines:
        db.add(
            JournalLine(
                journal_id=journal.id,
                line_no=line.line_no,
                account_id=line.account_id,
                debit=line.debit,
                credit=line.credit,
                description=line.description,
                customer_id=line.customer_id,
                vendor_id=line.vendor_id,
            )
        )
    db.flush()
    db.refresh(journal)

    db.add(
        AuditEvent(
            org_id=ctx.org_id,
            entity_id=entity.id,
            actor_user_id=ctx.user.id,
            source="api",
            action="journal.create",
            target_kind="journal",
            target_id=journal.id,
            after={"journal_no": journal.journal_no, "lines": len(payload.lines)},
        )
    )

    if post:
        try:
            post_journal(db, journal.id, actor_user_id=ctx.user.id)
        except PostingError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    db.refresh(journal)
    return JournalOut.model_validate(journal)


@router.post("/{journal_id}/post", response_model=JournalOut)
def post_journal_route(
    journal_id: UUID,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> JournalOut:
    journal = db.get(Journal, journal_id)
    if journal is None or journal.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Journal not found")
    try:
        post_journal(db, journal.id, actor_user_id=ctx.user.id)
    except PostingError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(journal)
    return JournalOut.model_validate(journal)


@router.post("/{journal_id}/reverse", response_model=JournalOut)
def reverse_journal_route(
    journal_id: UUID,
    posting_date: date | None = None,
    memo: str | None = None,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> JournalOut:
    journal = db.get(Journal, journal_id)
    if journal is None or journal.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Journal not found")
    try:
        reversal = reverse_journal(
            db,
            journal.id,
            actor_user_id=ctx.user.id,
            posting_date=posting_date,
            memo=memo,
        )
    except PostingError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(reversal)
    return JournalOut.model_validate(reversal)
