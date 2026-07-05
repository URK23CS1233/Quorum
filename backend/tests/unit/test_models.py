"""Unit tests for the Pydantic data models."""

import pytest
from pydantic import ValidationError

from models import (
    Deployment, Incident, Metrics, QuorumAnalysis,
    IngestDeploymentRequest, IngestIncidentRequest,
    RollbackRequest, SimulateIncidentRequest,
)


# ── Deployment ────────────────────────────────────────────────────
def test_deployment_defaults_and_factories():
    d = Deployment(
        commit_sha="abc1234", commit_message="fix", author="Alice",
        services_affected=["api"], cpu_at_deploy=30.0,
        error_rate_at_deploy=0.1, latency_at_deploy=100.0,
    )
    assert d.id.startswith("dep-")
    assert len(d.id) == len("dep-") + 8
    assert d.status == "STABLE"
    assert d.branch == "main"
    assert d.repo == ""
    # timestamp is an ISO string
    assert "T" in d.timestamp


def test_deployment_unique_ids():
    kw = dict(commit_sha="a", commit_message="m", author="x",
              services_affected=[], cpu_at_deploy=1.0,
              error_rate_at_deploy=0.0, latency_at_deploy=1.0)
    assert Deployment(**kw).id != Deployment(**kw).id


def test_deployment_rejects_invalid_status():
    with pytest.raises(ValidationError):
        Deployment(
            commit_sha="a", commit_message="m", author="x",
            services_affected=[], cpu_at_deploy=1.0,
            error_rate_at_deploy=0.0, latency_at_deploy=1.0,
            status="EXPLODED",
        )


def test_deployment_requires_mandatory_fields():
    with pytest.raises(ValidationError):
        Deployment(commit_message="missing sha and others")


# ── Incident ──────────────────────────────────────────────────────
def test_incident_defaults():
    inc = Incident(
        triggered_by_deployment="dep-1", symptoms={"cpu": 90},
        root_cause="bad deploy", resolution="rollback",
        rolled_back_to_deployment="dep-0",
        rolled_back_to_commit="cafe123", time_to_resolve_minutes=5,
    )
    assert inc.id.startswith("inc-")
    assert inc.severity == "P2"


def test_incident_rejects_invalid_severity():
    with pytest.raises(ValidationError):
        Incident(
            triggered_by_deployment="dep-1", symptoms={},
            root_cause="c", resolution="r",
            rolled_back_to_deployment="dep-0", rolled_back_to_commit="x",
            time_to_resolve_minutes=1, severity="P9",
        )


# ── Metrics ───────────────────────────────────────────────────────
def test_metrics_default_status_healthy():
    m = Metrics(cpu=10, error_rate=0.1, latency_p99=90,
                requests_per_second=300, memory_usage=40)
    assert m.status == "healthy"


def test_metrics_accepts_valid_status():
    m = Metrics(cpu=90, error_rate=6, latency_p99=3000,
                requests_per_second=300, memory_usage=80, status="critical")
    assert m.status == "critical"


# ── QuorumAnalysis ────────────────────────────────────────────────
def test_quorum_analysis_defaults():
    qa = QuorumAnalysis(
        anomaly_type="error rate critical",
        current_metrics={"cpu": 50},
        recall_answer="answer",
        similar_incident_summary="summary",
        safe_state_deployment_id="dep-0",
        safe_state_commit="cafe",
        safe_state_commit_message="msg",
    )
    assert qa.confidence == "medium"
    assert qa.graph_insights == []
    assert qa.similar_incident_id is None
    assert "T" in qa.triggered_at


# ── Request wrappers ──────────────────────────────────────────────
def test_ingest_request_wrappers():
    dep = Deployment(commit_sha="a", commit_message="m", author="x",
                     services_affected=[], cpu_at_deploy=1.0,
                     error_rate_at_deploy=0.0, latency_at_deploy=1.0)
    req = IngestDeploymentRequest(deployment=dep)
    assert req.deployment.id == dep.id

    inc = Incident(triggered_by_deployment="d", symptoms={}, root_cause="c",
                   resolution="r", rolled_back_to_deployment="d0",
                   rolled_back_to_commit="x", time_to_resolve_minutes=1)
    assert IngestIncidentRequest(incident=inc).incident.id == inc.id


def test_rollback_request_default_reason():
    r = RollbackRequest(target_deployment_id="dep-1")
    assert "safe state" in r.reason.lower()


def test_simulate_request_default_and_validation():
    assert SimulateIncidentRequest().scenario == "error_storm"
    assert SimulateIncidentRequest(scenario="memory_leak").scenario == "memory_leak"
    with pytest.raises(ValidationError):
        SimulateIncidentRequest(scenario="nuclear_meltdown")
