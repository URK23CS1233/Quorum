"""Quorum — Auth Service"""

import secrets
import re
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from config import get_settings
from db_models import User, Organization, RefreshToken, UserRole

settings = get_settings()
pwd_ctx  = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Helpers ───────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def _make_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"

def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user.id, "email": user.email, "role": user.role.value,
         "org_id": user.org_id, "exp": expire},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM,
    )

def create_refresh_token(user: User, db: Session) -> str:
    token_str  = secrets.token_urlsafe(64)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    rt = RefreshToken(token=token_str, user_id=user.id, expires_at=expires_at)
    db.add(rt)
    db.commit()
    return token_str


# ── Register ──────────────────────────────────────────────────
def register(name: str, email: str, password: str, org_name: str, db: Session):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    # Create org (first user = SUPER_ADMIN)
    slug = _make_slug(org_name)
    existing_slugs = [r[0] for r in db.query(Organization.slug).all()]
    base, counter = slug, 1
    while slug in existing_slugs:
        slug = f"{base}-{counter}"; counter += 1

    org = Organization(name=org_name, slug=slug)
    db.add(org); db.flush()

    user = User(
        name=name, email=email,
        hashed_password=hash_password(password),
        org_id=org.id, role=UserRole.SUPER_ADMIN,
    )
    db.add(user); db.commit(); db.refresh(user)
    return user


# ── Login ─────────────────────────────────────────────────────
def login(email: str, password: str, db: Session):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    return user


# ── Refresh ───────────────────────────────────────────────────
def refresh_access_token(token_str: str, db: Session):
    rt = db.query(RefreshToken).filter(
        RefreshToken.token == token_str,
        RefreshToken.is_revoked == False,
    ).first()
    if not rt:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    # SQLite (the default store) returns naive datetimes; normalise to UTC-aware
    # before comparing so the token flow works across all configured databases.
    expires_at = rt.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.query(User).filter(User.id == rt.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Rotate: revoke old, issue new
    rt.is_revoked = True
    db.commit()
    return user


# ── Logout ────────────────────────────────────────────────────
def logout(token_str: str, db: Session):
    rt = db.query(RefreshToken).filter(RefreshToken.token == token_str).first()
    if rt:
        rt.is_revoked = True
        db.commit()
