"""Chart of accounts."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.accounting import Account
from ..models.audit import AuditEvent
from ..models.core import Entity
from ..schemas import AccountCreate, AccountOut
from ..security import AuthContext, require_org

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountOut])
def list_accounts(
    entity_id: UUID,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> list[AccountOut]:
    rows = (
        db.query(Account)
        .filter(Account.org_id == ctx.org_id, Account.entity_id == entity_id)
        .order_by(Account.code)
        .all()
    )
    return [AccountOut.model_validate(r) for r in rows]


@router.post("", response_model=AccountOut, status_code=201)
def create_account(
    payload: AccountCreate,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> AccountOut:
    entity = db.get(Entity, payload.entity_id)
    if entity is None or entity.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Entity not found")
    acct = Account(
        org_id=ctx.org_id,
        entity_id=payload.entity_id,
        code=payload.code,
        name=payload.name,
        type=payload.type,
        parent_id=payload.parent_id,
        currency=payload.currency,
        is_bank=payload.is_bank,
        is_cash=payload.is_cash,
        is_ar=payload.is_ar,
        is_ap=payload.is_ap,
    )
    db.add(acct)
    db.flush()
    db.add(
        AuditEvent(
            org_id=ctx.org_id,
            entity_id=entity.id,
            actor_user_id=ctx.user.id,
            source="api",
            action="account.create",
            target_kind="account",
            target_id=acct.id,
            after={"code": acct.code, "name": acct.name, "type": acct.type.value},
        )
    )
    db.commit()
    db.refresh(acct)
    return AccountOut.model_validate(acct)
