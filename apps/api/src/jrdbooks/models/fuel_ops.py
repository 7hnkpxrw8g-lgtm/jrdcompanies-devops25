"""Fuel-operations: tanks, deliveries, dispenses, variance."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, TimestampMixin, new_uuid


class FuelTank(Base, TimestampMixin):
    __tablename__ = "fuel_tank"
    __table_args__ = (UniqueConstraint("entity_id", "name", name="fuel_tank_entity_name"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    fuel_type: Mapped[str] = mapped_column(String(32), nullable=False)
    capacity_gallons: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    current_volume: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0"), nullable=False
    )
    weighted_avg_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), default=Decimal("0"), nullable=False
    )
    inventory_account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    cogs_account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class FuelDelivery(Base, TimestampMixin):
    __tablename__ = "fuel_delivery"
    __table_args__ = (Index("ix_fuel_delivery_tank_date", "tank_id", "delivery_date"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id"), nullable=False
    )
    tank_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("fuel_tank.id"), nullable=False
    )
    delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    vendor_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("vendor.id")
    )
    invoice_no: Mapped[str | None] = mapped_column(String(64))
    gallons: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    cost_per_gallon: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    journal_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("journal.id")
    )
    notes: Mapped[str | None] = mapped_column(Text)


class FuelDispense(Base, TimestampMixin):
    """Aggregated daily dispense reading (or single sale, depending on source)."""

    __tablename__ = "fuel_dispense"
    __table_args__ = (Index("ix_fuel_dispense_tank_date", "tank_id", "dispense_date"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id"), nullable=False
    )
    tank_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("fuel_tank.id"), nullable=False
    )
    dispense_date: Mapped[date] = mapped_column(Date, nullable=False)
    pump_id: Mapped[str | None] = mapped_column(String(32))
    gallons_sold: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    gross_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    stick_reading_gallons: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    variance_gallons: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0"), nullable=False
    )
    variance_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0"), nullable=False
    )
    journal_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("journal.id")
    )
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
