"""Audit log query endpoint (read-only)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.audit import AuditEvent
from ..security import AuthContext, require_org

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events")
def list_audit_events(
    target_kind: str | None = None,
    target_id: UUID | None = None,
    action: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> list[dict]:
    q = db.query(AuditEvent).filter(AuditEvent.org_id == ctx.org_id)
    if target_kind:
        q = q.filter(AuditEvent.target_kind == target_kind)
    if target_id:
        q = q.filter(AuditEvent.target_id == target_id)
    if action:
        q = q.filter(AuditEvent.action == action)
    rows = q.order_by(AuditEvent.occurred_at.desc()).limit(limit).all()
    return [
        {
            "id": str(r.id),
            "occurred_at": r.occurred_at.isoformat() if isinstance(r.occurred_at, datetime) else str(r.occurred_at),
            "actor_user_id": str(r.actor_user_id) if r.actor_user_id else None,
            "actor_label": r.actor_label,
            "source": r.source,
            "action": r.action,
            "target_kind": r.target_kind,
            "target_id": str(r.target_id) if r.target_id else None,
            "request_id": r.request_id,
            "before": r.before,
            "after": r.after,
        }
        for r in rows
    ]
