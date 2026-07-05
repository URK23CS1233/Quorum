"""Unit tests for the auth service (hashing, tokens, register/login/refresh)."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import jwt

import auth.service as svc
from config import get_settings
from db_models import User, Organization, RefreshToken, UserRole

settings = get_settings()


# ── password hashing ──────────────────────────────────────────────
def test_hash_and_verify_password():
    h = svc.hash_password("SuperSecret123")
    assert h != "SuperSecret123"
    assert svc.verify_password("SuperSecret123", h) is True
    assert svc.verify_password("wrong", h) is False


# ── slug generation ───────────────────────────────────────────────
@pytest.mark.parametrize("name,expected", [
    ("Acme Corp", "acme-corp"),
    ("  Weird__Name!! ", "weird-name"),
    ("", "org"),
    ("!!!", "org"),
])
def test_make_slug(name, expected):
    assert svc._make_slug(name) == expected


# ── access token ──────────────────────────────────────────────────
def test_create_access_token_encodes_claims():
    user = User(id="u1", email="a@b.com", name="A",
                role=UserRole.OPERATOR, org_id="o1", hashed_password="x")
    token = svc.create_access_token(user)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "u1"
    assert payload["email"] == "a@b.com"
    assert payload["role"] == "OPERATOR"
    assert payload["org_id"] == "o1"
    assert "exp" in payload


# ── refresh token ─────────────────────────────────────────────────
def test_create_refresh_token_persists(db_session):
    org = Organization(name="O", slug="o")
    db_session.add(org); db_session.flush()
    user = User(name="A", email="a@b.com", hashed_password="x",
                org_id=org.id, role=UserRole.VIEWER)
    db_session.add(user); db_session.commit()

    token = svc.create_refresh_token(user, db_session)
    stored = db_session.query(RefreshToken).filter_by(token=token).first()
    assert stored is not None
    assert stored.user_id == user.id
    assert stored.is_revoked is False


# ── register ──────────────────────────────────────────────────────
def test_register_creates_super_admin(db_session):
    user = svc.register("Alice", "alice@quorum.test", "password123", "Acme", db_session)
    assert user.role == UserRole.SUPER_ADMIN
    assert user.organization.slug == "acme"


def test_register_duplicate_email_raises(db_session):
    svc.register("Alice", "dup@quorum.test", "password123", "Acme", db_session)
    with pytest.raises(HTTPException) as exc:
        svc.register("Bob", "dup@quorum.test", "password123", "Beta", db_session)
    assert exc.value.status_code == 409


def test_register_short_password_raises(db_session):
    with pytest.raises(HTTPException) as exc:
        svc.register("Alice", "short@quorum.test", "short", "Acme", db_session)
    assert exc.value.status_code == 422


def test_register_generates_unique_slugs(db_session):
    u1 = svc.register("A", "a@q.test", "password123", "Acme", db_session)
    u2 = svc.register("B", "b@q.test", "password123", "Acme", db_session)
    assert u1.organization.slug == "acme"
    assert u2.organization.slug == "acme-1"


# ── login ─────────────────────────────────────────────────────────
def test_login_success(db_session):
    svc.register("Alice", "login@quorum.test", "password123", "Acme", db_session)
    user = svc.login("login@quorum.test", "password123", db_session)
    assert user.email == "login@quorum.test"


def test_login_wrong_password(db_session):
    svc.register("Alice", "wp@quorum.test", "password123", "Acme", db_session)
    with pytest.raises(HTTPException) as exc:
        svc.login("wp@quorum.test", "nope", db_session)
    assert exc.value.status_code == 401


def test_login_unknown_email(db_session):
    with pytest.raises(HTTPException) as exc:
        svc.login("ghost@quorum.test", "password123", db_session)
    assert exc.value.status_code == 401


def test_login_inactive_account(db_session):
    user = svc.register("Alice", "inactive@quorum.test", "password123", "Acme", db_session)
    user.is_active = False
    db_session.commit()
    with pytest.raises(HTTPException) as exc:
        svc.login("inactive@quorum.test", "password123", db_session)
    assert exc.value.status_code == 403


# ── refresh ───────────────────────────────────────────────────────
def test_refresh_rotates_token(db_session):
    user = svc.register("Alice", "refresh@quorum.test", "password123", "Acme", db_session)
    token = svc.create_refresh_token(user, db_session)

    refreshed_user = svc.refresh_access_token(token, db_session)
    assert refreshed_user.id == user.id

    old = db_session.query(RefreshToken).filter_by(token=token).first()
    assert old.is_revoked is True          # old token rotated out


def test_refresh_invalid_token(db_session):
    with pytest.raises(HTTPException) as exc:
        svc.refresh_access_token("not-a-real-token", db_session)
    assert exc.value.status_code == 401


def test_refresh_expired_token(db_session):
    user = svc.register("Alice", "exp@quorum.test", "password123", "Acme", db_session)
    rt = RefreshToken(
        token="expired-token", user_id=user.id,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(rt); db_session.commit()
    with pytest.raises(HTTPException) as exc:
        svc.refresh_access_token("expired-token", db_session)
    assert exc.value.status_code == 401


def test_refresh_revoked_token(db_session):
    user = svc.register("Alice", "rev@quorum.test", "password123", "Acme", db_session)
    token = svc.create_refresh_token(user, db_session)
    svc.logout(token, db_session)          # revoke it
    with pytest.raises(HTTPException) as exc:
        svc.refresh_access_token(token, db_session)
    assert exc.value.status_code == 401


# ── logout ────────────────────────────────────────────────────────
def test_logout_revokes_token(db_session):
    user = svc.register("Alice", "out@quorum.test", "password123", "Acme", db_session)
    token = svc.create_refresh_token(user, db_session)
    svc.logout(token, db_session)
    rt = db_session.query(RefreshToken).filter_by(token=token).first()
    assert rt.is_revoked is True


def test_logout_unknown_token_is_noop(db_session):
    svc.logout("nonexistent", db_session)  # should not raise
