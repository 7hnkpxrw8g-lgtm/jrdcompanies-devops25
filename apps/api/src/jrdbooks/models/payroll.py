"""Payroll: runs and payslips."""

from __future__ import annotations

import enum
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Index, Numeric, String, UniqueConstraint
from ..types import JSONColumn
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, TimestampMixin, new_uuid


class PayrollStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    PAID = "paid"
    VOID = "void"


class PayrollRun(Base, TimestampMixin):
    __tablename__ = "payroll_run"
    __table_args__ = (UniqueConstraint("entity_id", "run_no", name="payroll_entity_no"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id"), nullable=False
    )
    run_no: Mapped[str] = mapped_column(String(64), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    pay_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[PayrollStatus] = mapped_column(
        Enum(PayrollStatus, name="payroll_status_enum"),
        default=PayrollStatus.DRAFT,
        nullable=False,
    )
    gross_wages: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0"), nullable=False
    )
    employer_taxes: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0"), nullable=False
    )
    employee_taxes: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0"), nullable=False
    )
    net_pay: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0"), nullable=False
    )
    journal_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("journal.id")
    )

    payslips: Mapped[list["Payslip"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class Payslip(Base, TimestampMixin):
    __tablename__ = "payslip"
    __table_args__ = (Index("ix_payslip_run", "run_id"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False
    )
    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("payroll_run.id", ondelete="CASCADE"),
        nullable=False,
    )
    employee_name: Mapped[str] = mapped_column(String(255), nullable=False)
    employee_external_id: Mapped[str | None] = mapped_column(String(128))
    gross: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    employee_taxes: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    employer_taxes: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    net: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    deductions: Mapped[dict] = mapped_column(JSONColumn, default=dict, nullable=False)

    run: Mapped[PayrollRun] = relationship(back_populates="payslips")
