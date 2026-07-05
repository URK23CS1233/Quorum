"""Integration tests for the memory ingestion endpoints (operator-gated)."""

from unittest.mock import AsyncMock

from db_models import UserRole
from models import Deployment

DEPLOYMENT_BODY = {"deployment": {
    "commit_sha": "abc1234def", "commit_message": "add rate limiting",
    "author": "Alice", "services_affected": ["api-gateway"],
    "cpu_at_deploy": 30.0, "error_rate_at_deploy": 0.1, "latency_at_deploy": 100.0,
}}

INCIDENT_BODY = {"incident": {
    "triggered_by_deployment": "dep-1", "symptoms": {"cpu": 90, "error_rate": 12},
    "root_cause": "bad migration", "resolution": "rolled back",
    "rolled_back_to_deployment": "dep-0", "rolled_back_to_commit": "cafe",
    "time_to_resolve_minutes": 5, "severity": "P1",
}}


# ── deployment ────────────────────────────────────────────────────
def test_ingest_deployment_requires_auth(client):
    assert client.post("/api/memory/deployment", json=DEPLOYMENT_BODY).status_code == 401


def test_ingest_deployment_rejects_analyst(client, auth_header):
    r = client.post("/api/memory/deployment", headers=auth_header(UserRole.ANALYST),
                    json=DEPLOYMENT_BODY)
    assert r.status_code == 403


def test_ingest_deployment_success(client, auth_header):
    r = client.post("/api/memory/deployment", headers=auth_header(UserRole.OPERATOR),
                    json=DEPLOYMENT_BODY)
    assert r.status_code == 200
    assert r.json()["deployment_id"].startswith("dep-")


# ── incident ──────────────────────────────────────────────────────
def test_ingest_incident_success(client, auth_header):
    r = client.post("/api/memory/incident", headers=auth_header(UserRole.OPERATOR),
                    json=INCIDENT_BODY)
    assert r.status_code == 200
    assert r.json()["incident_id"].startswith("inc-")


# ── github ────────────────────────────────────────────────────────
def test_ingest_github_success(client, auth_header, monkeypatch):
    import github_service
    dep = Deployment(commit_sha="s", commit_message="m", author="a",
                     services_affected=["api"], cpu_at_deploy=1.0,
                     error_rate_at_deploy=0.0, latency_at_deploy=1.0)
    monkeypatch.setattr(github_service, "fetch_recent_commits",
                        AsyncMock(return_value=[dep]))
    r = client.post("/api/memory/github/octocat/hello",
                    headers=auth_header(UserRole.OPERATOR))
    assert r.status_code == 200
    assert r.json()["ingested"] == 1


def test_ingest_github_no_commits_returns_404(client, auth_header, monkeypatch):
    import github_service
    monkeypatch.setattr(github_service, "fetch_recent_commits",
                        AsyncMock(return_value=[]))
    r = client.post("/api/memory/github/octocat/empty",
                    headers=auth_header(UserRole.OPERATOR))
    assert r.status_code == 404


# ── improve / forget ──────────────────────────────────────────────
def test_improve_memory(client, auth_header):
    r = client.post("/api/memory/improve", headers=auth_header(UserRole.OPERATOR))
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_forget_memory(client, auth_header):
    r = client.request("DELETE", "/api/memory", headers=auth_header(UserRole.OPERATOR))
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_forget_memory_rejects_analyst(client, auth_header):
    r = client.request("DELETE", "/api/memory", headers=auth_header(UserRole.ANALYST))
    assert r.status_code == 403
