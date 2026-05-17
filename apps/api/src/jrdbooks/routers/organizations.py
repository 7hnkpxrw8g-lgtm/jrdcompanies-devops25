"""Organizations and entities."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.core import Entity, Organization
from ..schemas import EntityOut, OrganizationOut
from ..security import AuthContext, require_org

router = APIRouter(tags=["organizations"])


@router.get("/organizations/current", response_model=OrganizationOut)
def current_org(
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> OrganizationOut:
    org = db.get(Organization, ctx.org_id)
    assert org is not None
    return OrganizationOut.model_validate(org)


@router.get("/entities", response_model=list[EntityOut])
def list_entities(
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> list[EntityOut]:
    rows = db.query(Entity).filter(Entity.org_id == ctx.org_id).order_by(Entity.code).all()
    return [EntityOut.model_validate(r) for r in rows]
