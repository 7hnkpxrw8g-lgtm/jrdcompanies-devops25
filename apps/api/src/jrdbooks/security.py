"""Auth: password hashing, JWT, dependency for current user."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models.core import Membership, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(user_id: UUID, org_id: UUID | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {
        "sub": str(user_id),
        "org_id": str(org_id) if org_id else None,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class AuthContext:
    def __init__(self, user: User, org_id: UUID | None, role: str | None) -> None:
        self.user = user
        self.org_id = org_id
        self.role = role


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> AuthContext:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid auth credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        org_id = payload.get("org_id")
    except JWTError as exc:
        raise cred_exc from exc

    if not user_id:
        raise cred_exc

    user = db.get(User, UUID(user_id))
    if user is None or not user.is_active:
        raise cred_exc

    role = None
    org_uuid = UUID(org_id) if org_id else None
    if org_uuid:
        membership = (
            db.query(Membership)
            .filter(Membership.user_id == user.id, Membership.org_id == org_uuid)
            .first()
        )
        if membership is None:
            raise HTTPException(status_code=403, detail="Not a member of this organization")
        role = membership.role.value

    return AuthContext(user=user, org_id=org_uuid, role=role)


def require_org(ctx: AuthContext = Depends(get_current_user)) -> AuthContext:
    if ctx.org_id is None:
        raise HTTPException(status_code=400, detail="No organization context")
    return ctx
