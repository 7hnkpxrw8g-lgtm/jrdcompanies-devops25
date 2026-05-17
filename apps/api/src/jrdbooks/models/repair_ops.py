"""Repair-order tracking for auto-shop operations."""

from __future__ import annotations

import enum
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, TimestampMixin, new_uuid


class ROStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    AWAITING_PARTS = "awaiting_parts"
    READY = "ready"
    COMPLETED = "completed"
    INVOICED = "invoiced"
    CANCELLED = "cancelled"


class RepairOrder(Base, TimestampMixin):
    __tablename__ = "repair_order"
    __table_args__ = (UniqueConstraint("org_id", "ro_no", name="ro_org_no"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id"), nullable=False
    )
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customer.id"), nullable=False
    )
    ro_no: Mapped[str] = mapped_column(String(64), nullable=False)
    opened_date: Mapped[date] = mapped_column(Date, nullable=False)
    closed_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[ROStatus] = mapped_column(
        Enum(ROStatus, name="ro_status_enum"), default=ROStatus.DRAFT, nullable=False
    )
    vehicle_vin: Mapped[str | None] = mapped_column(String(32))
    vehicle_year: Mapped[int | None] = mapped_column(Integer)
    vehicle_make: Mapped[str | None] = mapped_column(String(64))
    vehicle_model: Mapped[str | None] = mapped_column(String(64))
    odometer_in: Mapped[int | None] = mapped_column(Integer)
    odometer_out: Mapped[int | None] = mapped_column(Integer)
    technician: Mapped[str | None] = mapped_column(String(255))
    labor_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0"), nullable=False
    )
    parts_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0"), nullable=False
    )
    tax_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0"), nullable=False
    )
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    invoice_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("invoice.id")
    )
    external_id: Mapped[str | None] = mapped_column(String(128))  # Tekmetric, etc.
    notes: Mapped[str | None] = mapped_column(Text)

    lines: Mapped[list[RepairOrderLine]] = relationship(
        back_populates="repair_order",
        cascade="all, delete-orphan",
        order_by="RepairOrderLine.line_no",
    )


class RepairOrderLine(Base, TimestampMixin):
    __tablename__ = "repair_order_line"
    __table_args__ = (Index("ix_ro_line_ro", "repair_order_id"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    repair_order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("repair_order.id", ondelete="CASCADE"), nullable=False
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # labor|part|fee
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    item_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_item.id")
    )

    repair_order: Mapped[RepairOrder] = relationship(back_populates="lines")
