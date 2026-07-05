"""Integration tests for the user-management API (admin-gated)."""

from db_models import UserRole


# NB: EmailStr rejects the reserved `.test` TLD, so invite bodies use a real one.
def _invite_body(email="invitee@quorum.io", role="VIEWER"):
    return {"name": "Invitee", "email": email, "password": "password123", "role": role}


# ── access control ────────────────────────────────────────────────
def test_list_users_requires_admin(client, auth_header):
    assert client.get("/api/users/").status_code == 401
    assert client.get("/api/users/", headers=auth_header(UserRole.OPERATOR)).status_code == 403


def test_list_users_returns_org_members(client, make_user):
    admin, token = make_user(role=UserRole.ADMIN)
    hdr = {"Authorization": f"Bearer {token}"}
    client.post("/api/users/invite", headers=hdr, json=_invite_body())
    r = client.get("/api/users/", headers=hdr)
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()}
    assert admin.email in emails and "invitee@quorum.io" in emails


# ── invite ────────────────────────────────────────────────────────
def test_invite_user_success(client, auth_header):
    r = client.post("/api/users/invite", headers=auth_header(UserRole.ADMIN),
                    json=_invite_body(role="ANALYST"))
    assert r.status_code == 201
    assert r.json()["role"] == "ANALYST"


def test_invite_duplicate_email(client, auth_header):
    hdr = auth_header(UserRole.ADMIN)
    client.post("/api/users/invite", headers=hdr, json=_invite_body())
    r = client.post("/api/users/invite", headers=hdr, json=_invite_body())
    assert r.status_code == 409


# ── update ────────────────────────────────────────────────────────
def test_update_user_role(client, make_user):
    admin, token = make_user(role=UserRole.ADMIN)
    hdr = {"Authorization": f"Bearer {token}"}
    invitee_id = client.post("/api/users/invite", headers=hdr,
                             json=_invite_body()).json()["id"]
    r = client.patch(f"/api/users/{invitee_id}", headers=hdr, json={"role": "OPERATOR"})
    assert r.status_code == 200
    assert r.json()["role"] == "OPERATOR"


def test_cannot_modify_self(client, make_user):
    admin, token = make_user(role=UserRole.ADMIN)
    hdr = {"Authorization": f"Bearer {token}"}
    r = client.patch(f"/api/users/{admin.id}", headers=hdr, json={"role": "VIEWER"})
    assert r.status_code == 400


def test_update_missing_user_404(client, auth_header):
    r = client.patch("/api/users/nonexistent", headers=auth_header(UserRole.ADMIN),
                     json={"role": "VIEWER"})
    assert r.status_code == 404


# ── deactivate ────────────────────────────────────────────────────
def test_deactivate_user(client, make_user):
    admin, token = make_user(role=UserRole.ADMIN)
    hdr = {"Authorization": f"Bearer {token}"}
    invitee_id = client.post("/api/users/invite", headers=hdr,
                             json=_invite_body()).json()["id"]
    r = client.delete(f"/api/users/{invitee_id}", headers=hdr)
    assert r.status_code == 200


def test_cannot_deactivate_self(client, make_user):
    admin, token = make_user(role=UserRole.ADMIN)
    hdr = {"Authorization": f"Bearer {token}"}
    r = client.delete(f"/api/users/{admin.id}", headers=hdr)
    assert r.status_code == 400


# ── audit log ─────────────────────────────────────────────────────
def test_audit_log_records_actions(client, make_user):
    admin, token = make_user(role=UserRole.ADMIN)
    hdr = {"Authorization": f"Bearer {token}"}
    client.post("/api/users/invite", headers=hdr, json=_invite_body())
    r = client.get("/api/users/audit-log", headers=hdr)
    assert r.status_code == 200
    actions = {entry["action"] for entry in r.json()}
    assert "user.invite" in actions
