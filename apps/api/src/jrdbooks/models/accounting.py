"""Double-entry accounting primitives: chart of accounts, journals, ledger."""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, TimestampMixin, new_uuid
from ..types import JSONColumn


class AccountType(str, enum.Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"
    CONTRA_ASSET = "contra_asset"
    CONTRA_LIABILITY = "contra_liability"
    CONTRA_REVENUE = "contra_revenue"


# Sign convention: which side increases the account?
NORMAL_BALANCE: dict[AccountType, str] = {
    AccountType.ASSET: "debit",
    AccountType.EXPENSE: "debit",
    AccountType.CONTRA_LIABILITY: "debit",
    AccountType.CONTRA_REVENUE: "debit",
    AccountType.LIABILITY: "credit",
    AccountType.EQUITY: "credit",
    AccountType.REVENUE: "credit",
    AccountType.CONTRA_ASSET: "credit",
}


class JournalStatus(str, enum.Enum):
    DRAFT = "draft"
    POSTED = "posted"
    REVERSED = "reversed"


class JournalSource(str, enum.Enum):
    MANUAL = "manual"
    INVOICE = "invoice"
    BILL = "bill"
    PAYMENT = "payment"
    BANK = "bank"
    PAYROLL = "payroll"
    FUEL = "fuel"
    INVENTORY = "inventory"
    INTEGRATION = "integration"
    SYSTEM = "system"


class Account(Base, TimestampMixin):
    """Chart of accounts entry, scoped by org+entity."""

    __tablename__ = "account"
    __table_args__ = (
        UniqueConstraint("entity_id", "code", name="account_entity_code"),
        Index("ix_account_org_entity", "org_id", "entity_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("account.id", ondelete="SET NULL")
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, name="account_type_enum"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_bank: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_cash: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_ar: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_ap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Journal(Base, TimestampMixin):
    """Header for a double-entry journal. Posting freezes lines + writes ledger entries."""

    __tablename__ = "journal"
    __table_args__ = (
        Index("ix_journal_org_entity_date", "org_id", "entity_id", "posting_date"),
        Index("ix_journal_status", "status"),
        CheckConstraint(
            "(status <> 'posted') OR (posted_at IS NOT NULL)",
            name="posted_requires_posted_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), nullable=False
    )
    journal_no: Mapped[str] = mapped_column(String(32), nullable=False)
    posting_date: Mapped[date] = mapped_column(Date, nullable=False)
    memo: Mapped[str | None] = mapped_column(Text)
    status: Mapped[JournalStatus] = mapped_column(
        Enum(JournalStatus, name="journal_status_enum"),
        default=JournalStatus.DRAFT,
        nullable=False,
    )
    source: Mapped[JournalSource] = mapped_column(
        Enum(JournalSource, name="journal_source_enum"),
        default=JournalSource.MANUAL,
        nullable=False,
    )
    source_ref: Mapped[str | None] = mapped_column(String(128))
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    fx_rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("1"), nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posted_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    reversed_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("journal.id", ondelete="SET NULL")
    )
    reverses_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("journal.id", ondelete="SET NULL")
    )
    extra: Mapped[dict] = mapped_column(JSONColumn, default=dict, nullable=False)

    lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="journal",
        cascade="all, delete-orphan",
        order_by="JournalLine.line_no",
    )


class JournalLine(Base, TimestampMixin):
    """One side of a journal. Stored before posting so drafts can be edited."""

    __tablename__ = "journal_line"
    __table_args__ = (
        CheckConstraint("debit >= 0", name="debit_nonneg"),
        CheckConstraint("credit >= 0", name="credit_nonneg"),
        CheckConstraint(
            "(debit = 0 AND credit > 0) OR (debit > 0 AND credit = 0)",
            name="debit_xor_credit",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    journal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("journal.id", ondelete="CASCADE"), nullable=False
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    customer_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    vendor_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    extra: Mapped[dict] = mapped_column(JSONColumn, default=dict, nullable=False)

    journal: Mapped[Journal] = relationship(back_populates="lines")


class LedgerEntry(Base):
    """Immutable, append-only ledger row. Written when a journal is posted.

    Once inserted, rows here are never updated or deleted. Reversals are new rows
    pointing at the original via `reverses_entry_id`.
    """

    __tablename__ = "ledger_entry"
    __table_args__ = (
        Index("ix_ledger_org_entity_account_date", "org_id", "entity_id", "account_id", "posting_date"),
        Index("ix_ledger_journal", "journal_id"),
        CheckConstraint("amount <> 0", name="amount_nonzero"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id"), nullable=False
    )
    journal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("journal.id"), nullable=False
    )
    journal_line_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("journal_line.id"), nullable=False
    )
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    posting_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Signed amount: positive = debit, negative = credit. Sums to zero per journal.
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    fx_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    reverses_entry_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ledger_entry.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PeriodClose(Base, TimestampMixin):
    """Snapshot of a closed fiscal period; rows in that period become read-only."""

    __tablename__ = "period_close"
    __table_args__ = (
        UniqueConstraint("entity_id", "fiscal_year", "fiscal_period", name="period_close_unique"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id"), nullable=False
    )
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_period: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    closed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    retained_earnings_journal_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("journal.id")
    )
    notes: Mapped[str | None] = mapped_column(Text)
