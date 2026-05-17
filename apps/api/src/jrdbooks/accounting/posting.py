"""Journal posting engine.

A journal moves through three states:

    draft -> posted -> reversed

`post_journal` validates the journal is balanced, locks the period, writes
immutable `ledger_entry` rows, updates `journal.status` to `posted`, and writes
an audit event. After posting, journal lines are frozen — corrections happen
via `reverse_journal`, which creates a brand-new offsetting journal.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.accounting import (
    Journal,
    JournalLine,
    JournalSource,
    JournalStatus,
    LedgerEntry,
    PeriodClose,
)
from ..models.audit import AuditEvent

ZERO = Decimal("0")


class PostingError(Exception):
    """Raised when a journal cannot be posted."""


def _ensure_balanced(lines: list[JournalLine]) -> None:
    if not lines:
        raise PostingError("Journal has no lines")
    if len(lines) < 2:
        raise PostingError("Journal must have at least two lines")
    debit_total = sum((ln.debit for ln in lines), ZERO)
    credit_total = sum((ln.credit for ln in lines), ZERO)
    if debit_total != credit_total:
        raise PostingError(
            f"Journal is not balanced: debits={debit_total} credits={credit_total}"
        )
    if debit_total == ZERO:
        raise PostingError("Journal totals are zero")
    for ln in lines:
        if ln.debit < ZERO or ln.credit < ZERO:
            raise PostingError(f"Line {ln.line_no}: negative debit or credit not allowed")
        if (ln.debit > ZERO) == (ln.credit > ZERO):
            raise PostingError(
                f"Line {ln.line_no}: must have exactly one of debit or credit non-zero"
            )


def _ensure_period_open(db: Session, entity_id: UUID, posting_date: date) -> None:
    closed = db.execute(
        select(PeriodClose)
        .where(PeriodClose.entity_id == entity_id)
        .where(PeriodClose.period_start <= posting_date)
        .where(PeriodClose.period_end >= posting_date)
    ).scalar_one_or_none()
    if closed:
        raise PostingError(
            f"Cannot post to closed period {closed.period_start}..{closed.period_end}"
        )


def post_journal(
    db: Session,
    journal_id: UUID,
    actor_user_id: UUID | None = None,
    request_id: str | None = None,
) -> Journal:
    """Validate and post a draft journal. Idempotent for already-posted journals."""
    journal = db.get(Journal, journal_id)
    if journal is None:
        raise PostingError(f"Journal {journal_id} not found")
    if journal.status == JournalStatus.POSTED:
        return journal
    if journal.status == JournalStatus.REVERSED:
        raise PostingError("Cannot post a reversed journal")

    _ensure_balanced(list(journal.lines))
    _ensure_period_open(db, journal.entity_id, journal.posting_date)

    fx_rate = journal.fx_rate or Decimal("1")

    for line in journal.lines:
        signed_amount = (line.debit - line.credit).quantize(Decimal("0.0001"))
        fx_amount = (signed_amount * fx_rate).quantize(Decimal("0.0001"))
        entry = LedgerEntry(
            org_id=journal.org_id,
            entity_id=journal.entity_id,
            journal_id=journal.id,
            journal_line_id=line.id,
            account_id=line.account_id,
            posting_date=journal.posting_date,
            amount=signed_amount,
            currency=journal.currency,
            fx_amount=fx_amount,
            description=line.description or journal.memo,
        )
        db.add(entry)

    journal.status = JournalStatus.POSTED
    journal.posted_at = datetime.now(UTC)
    journal.posted_by = actor_user_id

    db.add(
        AuditEvent(
            org_id=journal.org_id,
            entity_id=journal.entity_id,
            actor_user_id=actor_user_id,
            source="api",
            action="journal.post",
            target_kind="journal",
            target_id=journal.id,
            request_id=request_id,
            after={
                "journal_no": journal.journal_no,
                "posting_date": journal.posting_date.isoformat(),
                "status": journal.status.value,
                "lines": len(journal.lines),
            },
        )
    )

    db.flush()
    return journal


def reverse_journal(
    db: Session,
    journal_id: UUID,
    actor_user_id: UUID | None = None,
    posting_date: date | None = None,
    memo: str | None = None,
    request_id: str | None = None,
) -> Journal:
    """Create a new journal that reverses the supplied posted journal."""
    original = db.get(Journal, journal_id)
    if original is None:
        raise PostingError(f"Journal {journal_id} not found")
    if original.status != JournalStatus.POSTED:
        raise PostingError("Only posted journals can be reversed")
    if original.reversed_by_id is not None:
        raise PostingError("Journal is already reversed")

    reversal_date = posting_date or original.posting_date

    reversal = Journal(
        org_id=original.org_id,
        entity_id=original.entity_id,
        journal_no=f"{original.journal_no}-REV",
        posting_date=reversal_date,
        memo=memo or f"Reversal of {original.journal_no}",
        status=JournalStatus.DRAFT,
        source=JournalSource.SYSTEM,
        source_ref=str(original.id),
        currency=original.currency,
        fx_rate=original.fx_rate,
        reverses_id=original.id,
    )
    db.add(reversal)
    db.flush()

    for line in original.lines:
        rev_line = JournalLine(
            journal_id=reversal.id,
            line_no=line.line_no,
            account_id=line.account_id,
            debit=line.credit,
            credit=line.debit,
            description=f"Reversal: {line.description or ''}".strip(),
            customer_id=line.customer_id,
            vendor_id=line.vendor_id,
        )
        db.add(rev_line)
    db.flush()
    # Re-load lines so the relationship is populated.
    db.refresh(reversal)

    post_journal(db, reversal.id, actor_user_id=actor_user_id, request_id=request_id)

    original.reversed_by_id = reversal.id
    original.status = JournalStatus.REVERSED
    db.add(
        AuditEvent(
            org_id=original.org_id,
            entity_id=original.entity_id,
            actor_user_id=actor_user_id,
            source="api",
            action="journal.reverse",
            target_kind="journal",
            target_id=original.id,
            request_id=request_id,
            after={"reversal_journal_id": str(reversal.id)},
        )
    )
    db.flush()
    return reversal
