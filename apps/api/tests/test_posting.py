"""Posting engine invariants.

These are the most important tests in the codebase: if posting is broken,
the books are broken.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from jrdbooks.accounting import (
    PostingError,
    account_balance,
    post_journal,
    reverse_journal,
    trial_balance,
)
from jrdbooks.models.accounting import (
    Journal,
    JournalLine,
    JournalSource,
    JournalStatus,
    LedgerEntry,
    PeriodClose,
)

from .conftest import make_journal


def test_post_balanced_journal_writes_ledger_entries(db, seeded_org):
    j = make_journal(
        db, seeded_org, lines=[(seeded_org["cash"], 100, 0), (seeded_org["rev"], 0, 100)]
    )
    posted = post_journal(db, j.id)
    assert posted.status == JournalStatus.POSTED
    assert posted.posted_at is not None

    entries = db.query(LedgerEntry).filter(LedgerEntry.journal_id == j.id).all()
    assert len(entries) == 2
    assert sum(e.amount for e in entries) == Decimal("0")
    cash_entry = next(e for e in entries if e.account_id == seeded_org["cash"].id)
    assert cash_entry.amount == Decimal("100.0000")
    rev_entry = next(e for e in entries if e.account_id == seeded_org["rev"].id)
    assert rev_entry.amount == Decimal("-100.0000")


def test_post_rejects_unbalanced_journal(db, seeded_org):
    j = make_journal(
        db, seeded_org, lines=[(seeded_org["cash"], 100, 0), (seeded_org["rev"], 0, 50)]
    )
    with pytest.raises(PostingError, match="not balanced"):
        post_journal(db, j.id)


def test_post_rejects_single_line(db, seeded_org):
    j = make_journal(db, seeded_org, lines=[(seeded_org["cash"], 100, 0)])
    with pytest.raises(PostingError):
        post_journal(db, j.id)


def test_post_is_idempotent(db, seeded_org):
    j = make_journal(
        db, seeded_org, lines=[(seeded_org["cash"], 50, 0), (seeded_org["rev"], 0, 50)]
    )
    post_journal(db, j.id)
    initial_count = db.query(LedgerEntry).count()
    # Second post must not double-write.
    post_journal(db, j.id)
    assert db.query(LedgerEntry).count() == initial_count


def test_reverse_creates_offsetting_journal(db, seeded_org):
    j = make_journal(
        db, seeded_org, lines=[(seeded_org["cash"], 200, 0), (seeded_org["rev"], 0, 200)]
    )
    post_journal(db, j.id)
    reversal = reverse_journal(db, j.id)
    db.refresh(j)
    assert j.status == JournalStatus.REVERSED
    assert reversal.status == JournalStatus.POSTED
    assert reversal.reverses_id == j.id

    # After reversal, net balance on cash should be zero.
    assert account_balance(db, seeded_org["cash"].id) == Decimal("0")


def test_cannot_reverse_unposted_journal(db, seeded_org):
    j = make_journal(
        db, seeded_org, lines=[(seeded_org["cash"], 100, 0), (seeded_org["rev"], 0, 100)]
    )
    with pytest.raises(PostingError, match="Only posted"):
        reverse_journal(db, j.id)


def test_cannot_post_to_closed_period(db, seeded_org):
    today = date.today()
    db.add(
        PeriodClose(
            org_id=seeded_org["org"].id,
            entity_id=seeded_org["entity"].id,
            fiscal_year=today.year,
            fiscal_period=today.month,
            period_start=today.replace(day=1),
            period_end=today + timedelta(days=15),
        )
    )
    db.commit()
    j = make_journal(
        db, seeded_org, lines=[(seeded_org["cash"], 100, 0), (seeded_org["rev"], 0, 100)]
    )
    with pytest.raises(PostingError, match="closed period"):
        post_journal(db, j.id)


def test_trial_balance_balances(db, seeded_org):
    # Two journals: $200 revenue, $40 rent
    j1 = make_journal(
        db, seeded_org, lines=[(seeded_org["cash"], 200, 0), (seeded_org["rev"], 0, 200)]
    )
    post_journal(db, j1.id)
    j2 = make_journal(
        db, seeded_org, lines=[(seeded_org["exp"], 40, 0), (seeded_org["cash"], 0, 40)]
    )
    post_journal(db, j2.id)
    db.commit()

    rows = trial_balance(db, seeded_org["entity"].id)
    total_debit = sum(r["debit"] for r in rows)
    total_credit = sum(r["credit"] for r in rows)
    assert total_debit == total_credit
    assert total_debit > 0


def test_account_balance_respects_as_of(db, seeded_org):
    today = date.today()
    j_old = make_journal(
        db,
        seeded_org,
        lines=[(seeded_org["cash"], 50, 0), (seeded_org["rev"], 0, 50)],
        posting_date=today - timedelta(days=10),
    )
    post_journal(db, j_old.id)
    j_new = make_journal(
        db,
        seeded_org,
        lines=[(seeded_org["cash"], 100, 0), (seeded_org["rev"], 0, 100)],
        posting_date=today,
    )
    post_journal(db, j_new.id)

    bal_before = account_balance(db, seeded_org["cash"].id, as_of=today - timedelta(days=5))
    bal_today = account_balance(db, seeded_org["cash"].id, as_of=today)
    assert bal_before == Decimal("50.0000")
    assert bal_today == Decimal("150.0000")


def test_db_rejects_invalid_journal_line(db, seeded_org):
    """DB check constraint also enforces debit XOR credit."""
    from sqlalchemy.exc import IntegrityError

    j = Journal(
        org_id=seeded_org["org"].id,
        entity_id=seeded_org["entity"].id,
        journal_no="TEST-NEG",
        posting_date=date.today(),
        source=JournalSource.MANUAL,
    )
    db.add(j)
    db.flush()
    db.add(
        JournalLine(
            journal_id=j.id,
            line_no=1,
            account_id=seeded_org["cash"].id,
            debit=Decimal("10"),
            credit=Decimal("10"),  # both non-zero: must be rejected by DB
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
