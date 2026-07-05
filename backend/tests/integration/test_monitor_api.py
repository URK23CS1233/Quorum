"""Integration tests for the monitor endpoints."""

from db_models import UserRole
from models import QuorumAnalysis


def test_status_requires_auth(client):
    assert client.get("/api/monitor/status").status_code == 401


def test_status_ok_for_analyst(client, auth_header):
    r = client.get("/api/monitor/status", headers=auth_header(UserRole.ANALYST))
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "healthy"
    assert body["has_incident"] is False
    assert body["deployment_count"] == 0


def test_status_rejects_viewer(client, auth_header):
    r = client.get("/api/monitor/status", headers=auth_header(UserRole.VIEWER))
    assert r.status_code == 403


def test_incident_none_by_default(client, auth_header):
    r = client.get("/api/monitor/incident", headers=auth_header(UserRole.ANALYST))
    assert r.status_code == 200
    assert r.json()["active"] is False


def test_incident_reports_active(client, auth_header):
    import quorum_engine
    quorum_engine._active_incident = QuorumAnalysis(
        anomaly_type="error rate critical",
        current_metrics={"cpu": 90, "error_rate": 12},
        recall_answer="matched prior incident",
        similar_incident_summary="payment outage",
        safe_state_deployment_id="dep-0",
        safe_state_commit="cafe1234",
        safe_state_commit_message="known good",
    )
    r = client.get("/api/monitor/incident", headers=auth_header(UserRole.ANALYST))
    assert r.status_code == 200
    body = r.json()
    assert body["active"] is True
    assert body["analysis"]["safe_state_deployment_id"] == "dep-0"


def test_deployments_list_reflects_ingestion(client, auth_header):
    op = auth_header(UserRole.OPERATOR)
    empty = client.get("/api/monitor/deployments", headers=op)
    assert empty.json()["deployments"] == []

    client.post("/api/memory/deployment", headers=op, json={"deployment": {
        "commit_sha": "abc1234", "commit_message": "fix", "author": "Alice",
        "services_affected": ["api"], "cpu_at_deploy": 28.0,
        "error_rate_at_deploy": 0.08, "latency_at_deploy": 95.0,
    }})

    listed = client.get("/api/monitor/deployments", headers=op)
    assert len(listed.json()["deployments"]) == 1
