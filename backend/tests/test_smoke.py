"""Smoke test: validates the shared fixtures and app wiring load correctly."""


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root_endpoint(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "Quorum v2"


def test_make_user_factory(make_user):
    from db_models import UserRole

    user, token = make_user(role=UserRole.ADMIN)
    assert user.role == UserRole.ADMIN
    assert isinstance(token, str) and token.count(".") == 2


def test_authenticated_request(client, auth_header):
    from db_models import UserRole

    r = client.get("/api/monitor/status", headers=auth_header(UserRole.ANALYST))
    assert r.status_code == 200
