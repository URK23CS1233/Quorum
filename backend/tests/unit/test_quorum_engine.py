"""Unit tests for the Quorum core engine (anomaly detection + analysis)."""

from unittest.mock import AsyncMock

import pytest

import quorum_engine as qe
import cognee_service
import metrics_simulator
from models import Metrics, Deployment, QuorumAnalysis


def _metrics(cpu=28.0, error_rate=0.08, latency=95.0):
    return Metrics(cpu=cpu, error_rate=error_rate, latency_p99=latency,
                   requests_per_second=300, memory_usage=50)


def _stable_dep(dep_id="dep-safe"):
    return Deployment(
        id=dep_id, commit_sha="cafebabe1234", commit_message="known good build",
        author="Alice", services_affected=["api"], cpu_at_deploy=28.0,
        error_rate_at_deploy=0.08, latency_at_deploy=95.0, status="STABLE",
    )


# ── detect_anomaly ────────────────────────────────────────────────
def test_detect_anomaly_healthy_returns_none():
    assert qe.detect_anomaly(_metrics()) is None


def test_detect_anomaly_degraded_only_returns_none():
    # All elevated but none critical -> not surfaced as an incident.
    m = _metrics(cpu=70.0, error_rate=2.0, latency=600.0)
    assert qe.detect_anomaly(m) is None


def test_detect_anomaly_error_critical():
    desc = qe.detect_anomaly(_metrics(error_rate=6.0))
    assert desc is not None
    assert "error rate critical" in desc


def test_detect_anomaly_cpu_critical():
    desc = qe.detect_anomaly(_metrics(cpu=90.0))
    assert desc and "CPU critical" in desc


def test_detect_anomaly_latency_critical():
    desc = qe.detect_anomaly(_metrics(latency=2500.0))
    assert desc and "latency critical" in desc


# ── _score_confidence ─────────────────────────────────────────────
def test_score_confidence_high():
    result = {"answer": "x" * 250, "insights": [1, 2, 3]}
    assert qe._score_confidence(result, _stable_dep()) == "high"


def test_score_confidence_medium():
    result = {"answer": "x" * 100, "insights": []}
    assert qe._score_confidence(result, _stable_dep()) == "medium"


def test_score_confidence_low_without_safe_dep():
    result = {"answer": "x" * 250, "insights": [1, 2, 3]}
    assert qe._score_confidence(result, None) == "low"


def test_score_confidence_low_short_answer():
    assert qe._score_confidence({"answer": "", "insights": []}, None) == "low"


# ── _resolve_safe_state ───────────────────────────────────────────
async def test_resolve_safe_state_uses_hint_when_present():
    dep = _stable_dep("dep-hinted")
    await cognee_service.remember_deployment(dep)
    resolved = qe._resolve_safe_state({"safe_deployment_hint": "dep-hinted"})
    assert resolved is not None and resolved.id == "dep-hinted"


async def test_resolve_safe_state_falls_back_to_last_stable():
    dep = _stable_dep("dep-stable")
    await cognee_service.remember_deployment(dep)
    # Hint points at a non-existent deployment -> fall back to last stable.
    resolved = qe._resolve_safe_state({"safe_deployment_hint": "dep-missing"})
    assert resolved is not None and resolved.id == "dep-stable"


async def test_resolve_safe_state_no_hint_uses_last_stable():
    await cognee_service.remember_deployment(_stable_dep("dep-x"))
    resolved = qe._resolve_safe_state({})
    assert resolved is not None and resolved.id == "dep-x"


# ── _build_summary ────────────────────────────────────────────────
def test_build_summary_prefers_summaries():
    assert qe._build_summary({"summaries": ["a" * 400]}) == "a" * 300


def test_build_summary_falls_back_to_answer():
    assert qe._build_summary({"answer": "an answer"}) == "an answer"


def test_build_summary_default_when_empty():
    assert "No similar incident" in qe._build_summary({})


# ── run_analysis ──────────────────────────────────────────────────
async def test_run_analysis_builds_analysis(monkeypatch):
    await cognee_service.remember_deployment(_stable_dep("dep-safe"))
    monkeypatch.setattr(cognee_service, "recall", AsyncMock(return_value={
        "answer": "y" * 250,
        "insights": [{"subject": "a"}, {"subject": "b"}, {"subject": "c"}],
        "summaries": ["a matching incident summary"],
        "safe_deployment_hint": "dep-safe",
    }))

    m = _metrics(error_rate=6.0)
    analysis = await qe.run_analysis(m, "error rate critical (6.0%)")

    assert isinstance(analysis, QuorumAnalysis)
    assert analysis.anomaly_type == "error rate critical (6.0%)"
    assert analysis.safe_state_deployment_id == "dep-safe"
    assert analysis.safe_state_commit == "cafebabe1234"
    assert analysis.confidence == "high"
    assert analysis.current_metrics["error_rate"] == 6.0


async def test_run_analysis_without_memory_marks_unknown(monkeypatch):
    monkeypatch.setattr(cognee_service, "recall", AsyncMock(return_value={
        "answer": "", "insights": [], "summaries": [], "safe_deployment_hint": None,
    }))
    analysis = await qe.run_analysis(_metrics(error_rate=6.0), "error critical")
    assert analysis.safe_state_deployment_id == "unknown"
    assert analysis.confidence == "low"


# ── execute_rollback ──────────────────────────────────────────────
async def test_execute_rollback_unknown_deployment():
    result = await qe.execute_rollback("dep-nope", "reason")
    assert result["status"] == "error"
    assert "not found" in result["message"]


async def test_execute_rollback_success_without_active_incident(cognee_stub):
    await cognee_service.remember_deployment(_stable_dep("dep-safe"))
    cognee_stub.add.reset_mock()               # ignore the setup ingestion
    result = await qe.execute_rollback("dep-safe", "manual rollback")
    assert result["status"] == "ok"
    assert result["deployment_id"] == "dep-safe"
    assert result["commit"] == "cafebabe1234"
    # No active incident -> nothing new was learned.
    cognee_stub.add.assert_not_called()


async def test_execute_rollback_learns_from_active_incident(cognee_stub):
    await cognee_service.remember_deployment(_stable_dep("dep-safe"))
    qe._active_incident = QuorumAnalysis(
        anomaly_type="error rate critical",
        current_metrics={"cpu": 90, "error_rate": 12},
        recall_answer="matched a prior payment outage",
        similar_incident_summary="summary",
        safe_state_deployment_id="dep-safe",
        safe_state_commit="cafebabe1234",
        safe_state_commit_message="known good build",
    )

    result = await qe.execute_rollback("dep-safe", "confirmed rollback")

    assert result["status"] == "ok"
    assert qe.get_active_incident() is None       # cleared after rollback
    cognee_stub.add.assert_awaited()              # incident was remembered
    metrics_simulator_mode = metrics_simulator.current_mode()
    assert metrics_simulator_mode == "healthy"    # incident resolved


# ── history accessors ─────────────────────────────────────────────
def test_active_incident_accessors():
    assert qe.get_active_incident() is None
    qe._active_incident = QuorumAnalysis(
        anomaly_type="x", current_metrics={}, recall_answer="a",
        similar_incident_summary="s", safe_state_deployment_id="d",
        safe_state_commit="c", safe_state_commit_message="m",
    )
    assert qe.get_active_incident() is not None
    qe.clear_active_incident()
    assert qe.get_active_incident() is None


def test_incident_history_is_capped():
    qe._incident_history.clear()
    for _ in range(25):
        qe._incident_history.append("x")
    assert len(qe.get_incident_history()) == 20
