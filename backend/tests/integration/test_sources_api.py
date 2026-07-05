"""Integration tests for the data-sources API."""

from db_models import UserRole


def _create(client, hdr, name="gh", source_type="github", config=None):
    return client.post("/api/sources/", headers=hdr, json={
        "name": name, "source_type": source_type,
        "config": config or {"owner": "octocat", "repo": "hello", "token": "secret"},
    })


# ── create ────────────────────────────────────────────────────────
def test_create_source_requires_operator(client, auth_header):
    assert _create(client, {}).status_code == 401
    assert _create(client, auth_header(UserRole.ANALYST)).status_code == 403


def test_create_source_success_and_redacts_secrets(client, auth_header):
    r = _create(client, auth_header(UserRole.OPERATOR))
    assert r.status_code == 201
    body = r.json()
    assert body["source_type"] == "github"
    # token must be redacted in the preview
    assert body["config_preview"]["token"] == "***"
    assert body["config_preview"]["owner"] == "octocat"


def test_create_source_invalid_type(client, auth_header):
    r = client.post("/api/sources/", headers=auth_header(UserRole.OPERATOR),
                    json={"name": "x", "source_type": "smoke-signals", "config": {}})
    assert r.status_code == 400


# ── list ──────────────────────────────────────────────────────────
def test_list_sources_for_analyst(client, make_user):
    op, op_token = make_user(role=UserRole.OPERATOR)
    hdr = {"Authorization": f"Bearer {op_token}"}
    _create(client, hdr)
    # analyst in the SAME org can list
    analyst, an_token = make_user(role=UserRole.ANALYST, org=op.organization)
    r = client.get("/api/sources/", headers={"Authorization": f"Bearer {an_token}"})
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_list_sources_isolated_by_org(client, make_user):
    op1, t1 = make_user(role=UserRole.OPERATOR)
    _create(client, {"Authorization": f"Bearer {t1}"})
    op2, t2 = make_user(role=UserRole.OPERATOR)          # different org
    r = client.get("/api/sources/", headers={"Authorization": f"Bearer {t2}"})
    assert r.json() == []


# ── update / delete / sync ────────────────────────────────────────
def test_update_source(client, auth_header):
    hdr = auth_header(UserRole.OPERATOR)
    sid = _create(client, hdr).json()["id"]
    r = client.patch(f"/api/sources/{sid}", headers=hdr,
                     json={"name": "renamed", "is_active": False})
    assert r.status_code == 200
    assert r.json()["name"] == "renamed"
    assert r.json()["is_active"] is False


def test_update_missing_source_404(client, auth_header):
    r = client.patch("/api/sources/nope", headers=auth_header(UserRole.OPERATOR),
                     json={"name": "x"})
    assert r.status_code == 404


def test_delete_source(client, auth_header):
    hdr = auth_header(UserRole.OPERATOR)
    sid = _create(client, hdr).json()["id"]
    assert client.delete(f"/api/sources/{sid}", headers=hdr).status_code == 200
    assert client.get("/api/sources/", headers=hdr).json() == []


def test_sync_source_triggers(client, auth_header):
    hdr = auth_header(UserRole.OPERATOR)
    # a manual source performs no network I/O when synced
    sid = _create(client, hdr, source_type="manual", config={}).json()["id"]
    r = client.post(f"/api/sources/{sid}/sync", headers=hdr)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_sync_missing_source_404(client, auth_header):
    r = client.post("/api/sources/nope/sync", headers=auth_header(UserRole.OPERATOR))
    assert r.status_code == 404
