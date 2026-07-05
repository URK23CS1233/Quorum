"""Integration tests for the auth API (register / login / me / refresh / logout)."""

REG = {
    "name": "Test User",
    "email": "test@quorum.ai",
    "password": "TestPass123",
    "org_name": "TestOrg",
}


def _register(client, **overrides):
    return client.post("/api/auth/register", json={**REG, **overrides})


# ── register ──────────────────────────────────────────────────────
def test_register_success(client):
    r = _register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_register_duplicate_email(client):
    _register(client)
    r = _register(client)
    assert r.status_code == 409


def test_register_short_password(client):
    r = _register(client, password="short")
    assert r.status_code == 422


def test_register_invalid_email(client):
    r = _register(client, email="not-an-email")
    assert r.status_code == 422


# ── login ─────────────────────────────────────────────────────────
def test_login_success(client):
    _register(client)
    r = client.post("/api/auth/login",
                    json={"email": REG["email"], "password": REG["password"]})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_wrong_password(client):
    _register(client)
    r = client.post("/api/auth/login",
                    json={"email": REG["email"], "password": "WrongPass!"})
    assert r.status_code == 401


def test_login_unknown_email(client):
    r = client.post("/api/auth/login",
                    json={"email": "ghost@quorum.ai", "password": "whatever12"})
    assert r.status_code == 401


# ── me ────────────────────────────────────────────────────────────
def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_profile(client):
    token = _register(client).json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == REG["email"]
    assert body["role"] == "SUPER_ADMIN"          # first user owns the org
    assert body["org_name"] == "TestOrg"


def test_me_with_bad_token(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer nonsense"})
    assert r.status_code == 401


# ── refresh / logout ──────────────────────────────────────────────
def test_refresh_returns_new_tokens(client):
    refresh_token = _register(client).json()["refresh_token"]
    r = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_refresh_rotation_invalidates_old_token(client):
    refresh_token = _register(client).json()["refresh_token"]
    client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    # old token was rotated out on first use
    r = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 401


def test_logout_revokes_refresh_token(client):
    refresh_token = _register(client).json()["refresh_token"]
    assert client.post("/api/auth/logout",
                       json={"refresh_token": refresh_token}).status_code == 200
    r = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 401


# ── profile / password ────────────────────────────────────────────
def test_update_profile(client):
    token = _register(client).json()["access_token"]
    r = client.put("/api/auth/me", headers={"Authorization": f"Bearer {token}"},
                   json={"name": "Renamed"})
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"


def test_change_password_success_then_login(client):
    token = _register(client).json()["access_token"]
    r = client.post("/api/auth/change-password",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"current_password": REG["password"], "new_password": "NewPass456"})
    assert r.status_code == 200
    # old password no longer works, new one does
    assert client.post("/api/auth/login",
                       json={"email": REG["email"], "password": REG["password"]}).status_code == 401
    assert client.post("/api/auth/login",
                       json={"email": REG["email"], "password": "NewPass456"}).status_code == 200


def test_change_password_wrong_current(client):
    token = _register(client).json()["access_token"]
    r = client.post("/api/auth/change-password",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"current_password": "wrong", "new_password": "NewPass456"})
    assert r.status_code == 400
