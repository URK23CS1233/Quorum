"""
Quorum — Auth integration tests
Run: cd backend && pytest test_auth.py -v
(stubs loaded automatically via conftest.py)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app

TEST_DB = "/tmp/test_quorum.db"
TEST_DB_URL = f"sqlite:///{TEST_DB}"
_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
_Session = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
Base.metadata.create_all(bind=_engine)


def _override_db():
    db = _Session()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_db
client = TestClient(app, raise_server_exceptions=False)

REG = {
    "name": "Test User",
    "email": "test@quorum.ai",
    "password": "TestPass123",
    "org_name": "TestOrg",
}


# ── tests ──────────────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_success():
    r = client.post("/api/auth/register", json=REG)
    assert r.status_code == 201
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_register_duplicate_email():
    client.post("/api/auth/register", json=REG)
    r = client.post("/api/auth/register", json=REG)
    assert r.status_code in (409, 400)


def test_login_success():
    client.post("/api/auth/register", json=REG)
    r = client.post("/api/auth/login", json={
        "email": REG["email"],
        "password": REG["password"],
    })
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password():
    client.post("/api/auth/register", json=REG)
    r = client.post("/api/auth/login", json={
        "email": REG["email"],
        "password": "WrongPassword!",
    })
    assert r.status_code in (401, 400)


def test_protected_route_without_token():
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_protected_route_with_token():
    client.post("/api/auth/register", json=REG)
    login_r = client.post("/api/auth/login", json={
        "email": REG["email"],
        "password": REG["password"],
    })
    token = login_r.json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == REG["email"]


def test_monitor_requires_auth():
    r = client.get("/api/monitor/status")
    assert r.status_code == 401


# ── teardown ───────────────────────────────────────────────────

def teardown_module():
    import pathlib
    pathlib.Path(TEST_DB).unlink(missing_ok=True)
