"""Period close: lock a fiscal period against further posting."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.accounting import PeriodClose
from ..models.audit import AuditEvent
from ..models.core import Entity
from ..security import AuthContext, require_org

router = APIRouter(prefix="/periods", tags=["periods"])


class PeriodCloseRequest(BaseModel):
    entity_id: UUID
    fiscal_year: int
    fiscal_period: int
    period_start: date
    period_end: date
    notes: str | None = None


@router.get("")
def list_closed_periods(
    entity_id: UUID | None = None,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> list[dict]:
    q = db.query(PeriodClose).filter(PeriodClose.org_id == ctx.org_id)
    if entity_id:
        q = q.filter(PeriodClose.entity_id == entity_id)
    rows = q.order_by(PeriodClose.period_end.desc()).all()
    return [
        {
            "id": str(r.id),
            "entity_id": str(r.entity_id),
            "fiscal_year": r.fiscal_year,
            "fiscal_period": r.fiscal_period,
            "period_start": r.period_start.isoformat(),
            "period_end": r.period_end.isoformat(),
            "closed_at": r.closed_at.isoformat(),
            "closed_by": str(r.closed_by) if r.closed_by else None,
        }
        for r in rows
    ]


@router.post("/close", status_code=201)
def close_period(
    payload: PeriodCloseRequest,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> dict:
    entity = db.get(Entity, payload.entity_id)
    if entity is None or entity.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Entity not found")
    if payload.period_end < payload.period_start:
        raise HTTPException(status_code=400, detail="period_end before period_start")

    existing = (
        db.query(PeriodClose)
        .filter(
            PeriodClose.entity_id == entity.id,
            PeriodClose.fiscal_year == payload.fiscal_year,
            PeriodClose.fiscal_period == payload.fiscal_period,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Period already closed")

    close = PeriodClose(
        org_id=ctx.org_id,
        entity_id=entity.id,
        fiscal_year=payload.fiscal_year,
        fiscal_period=payload.fiscal_period,
        period_start=payload.period_start,
        period_end=payload.period_end,
        closed_by=ctx.user.id,
        notes=payload.notes,
    )
    db.add(close)
    db.flush()
    db.add(
        AuditEvent(
            org_id=ctx.org_id,
            entity_id=entity.id,
            actor_user_id=ctx.user.id,
            source="api",
            action="period.close",
            target_kind="period_close",
            target_id=close.id,
            after={
                "fiscal_year": close.fiscal_year,
                "fiscal_period": close.fiscal_period,
                "period_start": close.period_start.isoformat(),
                "period_end": close.period_end.isoformat(),
            },
        )
    )
    db.commit()
    db.refresh(close)
    return {
        "id": str(close.id),
        "entity_id": str(close.entity_id),
        "fiscal_year": close.fiscal_year,
        "fiscal_period": close.fiscal_period,
        "period_start": close.period_start.isoformat(),
        "period_end": close.period_end.isoformat(),
        "closed_at": close.closed_at.isoformat(),
    }
