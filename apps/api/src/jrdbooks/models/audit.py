"""Append-only audit event log."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_uuid
from ..types import JSONColumn


class AuditEvent(Base):
    __tablename__ = "audit_event"
    __table_args__ = (
        Index("ix_audit_org_at", "org_id", "occurred_at"),
        Index("ix_audit_target", "target_kind", "target_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False
    )
    entity_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id")
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    actor_label: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    before: Mapped[dict] = mapped_column(JSONColumn, default=dict, nullable=False)
    after: Mapped[dict] = mapped_column(JSONColumn, default=dict, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONColumn, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
