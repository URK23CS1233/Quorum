"""Integration tests for health, security headers, CORS and the metrics WebSocket."""

import pytest
from starlette.websockets import WebSocketDisconnect

from db_models import UserRole


# ── health / root ─────────────────────────────────────────────────
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["mode"] == "healthy"


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "Quorum v2"


# ── security headers ──────────────────────────────────────────────
def test_security_headers_present(client):
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-XSS-Protection"] == "1; mode=block"
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in r.headers


def test_cors_allows_configured_origin(client):
    r = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


# ── websocket auth ────────────────────────────────────────────────
def test_ws_rejects_invalid_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/metrics?token=invalid-token"):
            pass


def test_ws_accepts_valid_token(client, make_user):
    _user, token = make_user(role=UserRole.ANALYST)
    # A valid token completes the handshake; closing the context tears it down.
    with client.websocket_connect(f"/ws/metrics?token={token}"):
        pass


def test_ws_accepts_without_token(client):
    # No token supplied -> auth is skipped, handshake still succeeds.
    with client.websocket_connect("/ws/metrics"):
        pass
