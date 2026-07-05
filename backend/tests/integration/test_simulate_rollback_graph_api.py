"""Integration tests for simulate, rollback and graph endpoints."""

from db_models import UserRole, AuditLog


DEPLOYMENT_BODY = {"deployment": {
    "commit_sha": "safe123commit", "commit_message": "last known good",
    "author": "Alice", "services_affected": ["api"], "cpu_at_deploy": 28.0,
    "error_rate_at_deploy": 0.08, "latency_at_deploy": 95.0,
}}


# ── simulate ──────────────────────────────────────────────────────
def test_simulate_incident_sets_critical_mode(client, auth_header):
    import metrics_simulator
    r = client.post("/api/simulate/incident", headers=auth_header(UserRole.OPERATOR),
                    json={"scenario": "error_storm"})
    assert r.status_code == 200
    assert r.json()["scenario"] == "error_storm"
    assert metrics_simulator.current_mode() == "critical"


def test_simulate_incident_invalid_scenario(client, auth_header):
    r = client.post("/api/simulate/incident", headers=auth_header(UserRole.OPERATOR),
                    json={"scenario": "meltdown"})
    assert r.status_code == 422


def test_simulate_incident_requires_operator(client, auth_header):
    r = client.post("/api/simulate/incident", headers=auth_header(UserRole.ANALYST),
                    json={"scenario": "error_storm"})
    assert r.status_code == 403


def test_simulate_resolve_restores_healthy(client, auth_header):
    import metrics_simulator
    op = auth_header(UserRole.OPERATOR)
    client.post("/api/simulate/incident", headers=op, json={"scenario": "cpu_spike"})
    r = client.post("/api/simulate/resolve", headers=op)
    assert r.status_code == 200
    assert metrics_simulator.current_mode() == "healthy"


# ── rollback ──────────────────────────────────────────────────────
def test_rollback_success_writes_audit_log(client, auth_header, db_session):
    op = auth_header(UserRole.OPERATOR)
    dep_id = client.post("/api/memory/deployment", headers=op,
                         json=DEPLOYMENT_BODY).json()["deployment_id"]

    r = client.post("/api/rollback", headers=op,
                    json={"target_deployment_id": dep_id, "reason": "manual"})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    logs = db_session.query(AuditLog).filter_by(action="rollback.execute").all()
    assert len(logs) == 1
    assert logs[0].resource == dep_id


def test_rollback_unknown_deployment_404(client, auth_header):
    r = client.post("/api/rollback", headers=auth_header(UserRole.OPERATOR),
                    json={"target_deployment_id": "dep-missing", "reason": "x"})
    assert r.status_code == 404


def test_rollback_requires_operator(client, auth_header):
    r = client.post("/api/rollback", headers=auth_header(UserRole.ANALYST),
                    json={"target_deployment_id": "dep-1"})
    assert r.status_code == 403


# ── graph ─────────────────────────────────────────────────────────
def test_graph_requires_analyst(client, auth_header):
    assert client.get("/api/graph").status_code == 401
    r = client.get("/api/graph", headers=auth_header(UserRole.VIEWER))
    assert r.status_code == 403


def test_graph_returns_structure(client, auth_header):
    r = client.get("/api/graph", headers=auth_header(UserRole.ANALYST))
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"nodes", "edges", "node_count", "edge_count"}
