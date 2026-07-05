"""Unit tests for FastAPI auth/RBAC dependencies."""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

import dependencies as deps
import auth.service as auth_svc
from db_models import User, Organization, UserRole


# ── _decode_token ─────────────────────────────────────────────────
def test_decode_token_valid():
    user = User(id="u1", email="a@b.com", name="A",
                role=UserRole.VIEWER, org_id="o1", hashed_password="x")
    token = auth_svc.create_access_token(user)
    payload = deps._decode_token(token)
    assert payload["sub"] == "u1"


def test_decode_token_invalid_raises_401():
    with pytest.raises(HTTPException) as exc:
        deps._decode_token("garbage.token.value")
    assert exc.value.status_code == 401


# ── require_role ──────────────────────────────────────────────────
def _user(role):
    return User(id="u", email="e@x.com", name="n",
                role=role, org_id="o", hashed_password="x")


async def test_require_role_allows_equal_level():
    result = await deps.require_operator(current_user=_user(UserRole.OPERATOR))
    assert result.role == UserRole.OPERATOR


async def test_require_role_allows_higher_level():
    # ADMIN (4) satisfies require_operator (3)
    result = await deps.require_operator(current_user=_user(UserRole.ADMIN))
    assert result.role == UserRole.ADMIN


async def test_require_role_rejects_lower_level():
    with pytest.raises(HTTPException) as exc:
        await deps.require_operator(current_user=_user(UserRole.VIEWER))
    assert exc.value.status_code == 403


async def test_require_admin_rejects_analyst():
    with pytest.raises(HTTPException) as exc:
        await deps.require_admin(current_user=_user(UserRole.ANALYST))
    assert exc.value.status_code == 403


# ── get_current_user ──────────────────────────────────────────────
def _seed_user(db, role=UserRole.OPERATOR, is_active=True):
    org = Organization(name="O", slug="o")
    db.add(org); db.flush()
    user = User(name="A", email="cu@quorum.test",
                hashed_password=auth_svc.hash_password("password123"),
                org_id=org.id, role=role, is_active=is_active)
    db.add(user); db.commit(); db.refresh(user)
    return user


async def test_get_current_user_valid(db_session):
    user = _seed_user(db_session)
    token = auth_svc.create_access_token(user)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    result = await deps.get_current_user(credentials=creds, db=db_session)
    assert result.id == user.id
    assert result.last_active is not None      # updated on access


async def test_get_current_user_no_credentials(db_session):
    with pytest.raises(HTTPException) as exc:
        await deps.get_current_user(credentials=None, db=db_session)
    assert exc.value.status_code == 401


async def test_get_current_user_bad_token(db_session):
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token")
    with pytest.raises(HTTPException) as exc:
        await deps.get_current_user(credentials=creds, db=db_session)
    assert exc.value.status_code == 401


async def test_get_current_user_inactive(db_session):
    user = _seed_user(db_session, is_active=False)
    token = auth_svc.create_access_token(user)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        await deps.get_current_user(credentials=creds, db=db_session)
    assert exc.value.status_code == 401


async def test_get_current_user_deleted(db_session):
    user = _seed_user(db_session)
    token = auth_svc.create_access_token(user)
    db_session.delete(user); db_session.commit()
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        await deps.get_current_user(credentials=creds, db=db_session)
    assert exc.value.status_code == 401
