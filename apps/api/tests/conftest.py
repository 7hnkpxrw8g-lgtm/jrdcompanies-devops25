"""Shared pytest fixtures.

The full integration suite uses Postgres (set DATABASE_URL). Local-only fast
tests use an in-memory SQLite by setting JRDBOOKS_TEST_BACKEND=sqlite.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Force a unique test database name so we don't trample dev.
os.environ.setdefault(
    "DATABASE_URL",
    f"postgresql+psycopg://jrd:jrd@localhost:5432/jrdbooks_test_{uuid.uuid4().hex[:8]}",
)

from jrdbooks.db import Base  # noqa: E402
from jrdbooks.models import (  # noqa: E402, F401
    Account,
    Entity,
    Organization,
)
from jrdbooks.models.accounting import AccountType, Journal, JournalLine, JournalSource


@pytest.fixture
def engine():
    """Use SQLite in-memory for fast unit tests of pure-Python logic."""
    eng = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine) -> Generator[Session, None, None]:
    SessionLocalTest = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    s = SessionLocalTest()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def seeded_org(db):
    org = Organization(slug="t", name="Test Org", base_currency="USD")
    db.add(org)
    db.flush()
    entity = Entity(org_id=org.id, code="ENT", name="Test Entity", currency="USD")
    db.add(entity)
    db.flush()
    cash = Account(
        org_id=org.id, entity_id=entity.id, code="1010", name="Cash",
        type=AccountType.ASSET, is_cash=True,
    )
    rev = Account(
        org_id=org.id, entity_id=entity.id, code="4000", name="Revenue",
        type=AccountType.REVENUE,
    )
    exp = Account(
        org_id=org.id, entity_id=entity.id, code="6100", name="Rent",
        type=AccountType.EXPENSE,
    )
    db.add_all([cash, rev, exp])
    db.flush()
    db.commit()
    return {"org": org, "entity": entity, "cash": cash, "rev": rev, "exp": exp}


def make_journal(db, seeded, lines, posting_date=None, source=JournalSource.MANUAL):
    """Helper to build a journal for tests."""
    j = Journal(
        org_id=seeded["org"].id,
        entity_id=seeded["entity"].id,
        journal_no=f"TEST-{uuid.uuid4().hex[:6]}",
        posting_date=posting_date or date.today(),
        memo="Test journal",
        source=source,
    )
    db.add(j)
    db.flush()
    for i, (account, debit, credit) in enumerate(lines, start=1):
        db.add(
            JournalLine(
                journal_id=j.id,
                line_no=i,
                account_id=account.id,
                debit=Decimal(str(debit)),
                credit=Decimal(str(credit)),
            )
        )
    db.flush()
    db.refresh(j)
    return j
