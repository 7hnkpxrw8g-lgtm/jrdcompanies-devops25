"""Authentication: login, token, current-user, organization switching."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.core import Membership, Organization, User
from ..schemas import LoginRequest, MeResponse, TokenResponse
from ..security import AuthContext, create_access_token, get_current_user, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
        )

    membership = (
        db.query(Membership)
        .filter(Membership.user_id == user.id)
        .order_by(Membership.accepted_at.asc())
        .first()
    )
    org = db.get(Organization, membership.org_id) if membership else None

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, org.id if org else None),
        user_id=user.id,
        org_id=org.id if org else None,
        org_slug=org.slug if org else None,
    )


@router.get("/me", response_model=MeResponse)
def me(ctx: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)) -> MeResponse:
    org = db.get(Organization, ctx.org_id) if ctx.org_id else None
    return MeResponse(
        id=ctx.user.id,
        email=ctx.user.email,
        full_name=ctx.user.full_name,
        org_id=ctx.org_id,
        org_slug=org.slug if org else None,
        role=ctx.role,
    )
