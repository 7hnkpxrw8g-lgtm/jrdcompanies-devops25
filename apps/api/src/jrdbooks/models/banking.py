"""Bank accounts, feed transactions, reconciliation."""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from ..types import JSONColumn
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, TimestampMixin, new_uuid


class BankAccount(Base, TimestampMixin):
    __tablename__ = "bank_account"
    __table_args__ = (
        UniqueConstraint("org_id", "external_id", name="bank_account_ext"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id"), nullable=False
    )
    ledger_account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    institution: Mapped[str | None] = mapped_column(String(255))
    mask: Mapped[str | None] = mapped_column(String(8))
    account_type: Mapped[str] = mapped_column(String(32), default="checking", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128))
    provider: Mapped[str | None] = mapped_column(String(32))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class BankTxStatus(str, enum.Enum):
    UNRECONCILED = "unreconciled"
    MATCHED = "matched"
    POSTED = "posted"
    IGNORED = "ignored"


class BankTransaction(Base, TimestampMixin):
    """Bank feed line. Becomes a journal entry on match/categorize."""

    __tablename__ = "bank_transaction"
    __table_args__ = (
        UniqueConstraint("bank_account_id", "external_id", name="bank_tx_ext"),
        Index("ix_bank_tx_status", "status"),
        Index("ix_bank_tx_date", "txn_date"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id"), nullable=False
    )
    bank_account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bank_account.id"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(128))
    txn_date: Mapped[date] = mapped_column(Date, nullable=False)
    posted_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    merchant: Mapped[str | None] = mapped_column(String(255))
    # Positive = deposit/credit to bank, negative = withdrawal/debit
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[BankTxStatus] = mapped_column(
        Enum(BankTxStatus, name="bank_tx_status_enum"),
        default=BankTxStatus.UNRECONCILED,
        nullable=False,
    )
    journal_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("journal.id")
    )
    suggested_account_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("account.id")
    )
    ai_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    raw: Mapped[dict] = mapped_column(JSONColumn, default=dict, nullable=False)


class ReconciliationMatch(Base, TimestampMixin):
    """Records a match between a bank transaction and a ledger entry."""

    __tablename__ = "reconciliation_match"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False
    )
    bank_transaction_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bank_transaction.id"), nullable=False, unique=True
    )
    ledger_entry_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ledger_entry.id"), nullable=False
    )
    matched_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("1.0"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
