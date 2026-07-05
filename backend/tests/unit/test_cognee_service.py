"""Unit tests for the Cognee memory service."""

from unittest.mock import AsyncMock

import pytest

import cognee_service as cs
from models import Deployment, Incident


def _dep(dep_id="dep-1", status="STABLE", sha="cafebabe1234"):
    return Deployment(
        id=dep_id, commit_sha=sha, commit_message="a good build",
        author="Alice", services_affected=["api", "db"], cpu_at_deploy=28.0,
        error_rate_at_deploy=0.08, latency_at_deploy=95.0, status=status,
    )


# ── text / insight / summary extraction ───────────────────────────
def test_extract_text_handles_none_and_str():
    assert cs._extract_text(None) == ""
    assert cs._extract_text("hello") == "hello"


def test_extract_text_joins_list_of_dicts():
    result = [{"text": "one"}, {"answer": "two"}, {"content": "three"}]
    assert cs._extract_text(result) == "one\n\ntwo\n\nthree"


def test_extract_text_list_of_non_dicts():
    assert cs._extract_text(["a", "b"]) == "a\n\nb"


def test_extract_insights_maps_node_neighbor():
    result = [{"node": {"name": "dep-1"}, "relationship": "caused",
               "neighbor": {"name": "inc-9"}}]
    insights = cs._extract_insights(result)
    assert insights == [{"subject": "dep-1", "relationship": "caused",
                         "object": "inc-9"}]


def test_extract_summaries():
    assert cs._extract_summaries([{"text": "s1"}, {"summary": "s2"}]) == ["s1", "s2"]


# ── name / label / group helpers ──────────────────────────────────
def test_safe_name_variants():
    assert cs._safe_name({"name": "n"}) == "n"
    assert cs._safe_name({"label": "l"}) == "l"
    assert cs._safe_name("raw") == "raw"
    assert cs._safe_name(None) == ""


def test_node_label_variants():
    assert cs._node_label({"name": "n"}) == "n"
    assert cs._node_label({"label": "l"}) == "l"
    assert cs._node_label({"id": "i"}) == "i"


@pytest.mark.parametrize("label,expected", [
    ("dep-123", "deployment"),
    ("inc-9", "incident"),
    ("commit sha", "commit"),
    ("payment-service", "service"),
    ("root cause here", "cause"),
    ("resolved by patch", "resolution"),
    ("something else", "concept"),
])
def test_node_group_classification(label, expected):
    assert cs._node_group(label, {}) == expected


# ── deployment registry ───────────────────────────────────────────
async def test_remember_deployment_persists_and_caches(cognee_stub):
    await cs.remember_deployment(_dep("dep-a"))
    assert cs.get_deployment("dep-a") is not None
    assert cs._REGISTRY_FILE.exists()
    cognee_stub.add.assert_awaited()
    cognee_stub.cognify.assert_awaited()


async def test_remember_stable_sets_last_stable():
    await cs.remember_deployment(_dep("dep-stable", status="STABLE"))
    assert cs.get_last_stable_deployment().id == "dep-stable"


async def test_remember_incident_ingests(cognee_stub):
    inc = Incident(
        triggered_by_deployment="dep-1", symptoms={"cpu": 90, "error_rate": 12},
        root_cause="bad migration", resolution="rolled back",
        rolled_back_to_deployment="dep-0", rolled_back_to_commit="deadbeef",
        time_to_resolve_minutes=4, severity="P1",
    )
    await cs.remember_incident(inc)
    cognee_stub.add.assert_awaited()
    cognee_stub.cognify.assert_awaited()


async def test_get_all_deployments():
    await cs.remember_deployment(_dep("dep-a"))
    await cs.remember_deployment(_dep("dep-b"))
    ids = {d.id for d in cs.get_all_deployments()}
    assert ids == {"dep-a", "dep-b"}


async def test_registry_survives_reload_from_file():
    await cs.remember_deployment(_dep("dep-persist"))
    cs._deployment_cache = None                       # force reload from disk
    assert cs.get_deployment("dep-persist") is not None


# ── recall ────────────────────────────────────────────────────────
async def test_recall_returns_structured_result(cognee_stub):
    cognee_stub.search = AsyncMock(return_value=[{"text": "matched"}])
    result = await cs.recall(cpu=90, error_rate=12, latency=3000,
                             anomaly_desc="error storm")
    assert result["answer"] == "matched"
    assert "insights" in result and "summaries" in result


async def test_recall_extracts_safe_deployment_hint(cognee_stub):
    await cs.remember_deployment(_dep("dep-safe", status="STABLE"))
    cognee_stub.search = AsyncMock(
        return_value=[{"text": "the safe state was dep-safe"}])
    result = await cs.recall(cpu=90, error_rate=12, latency=3000,
                             anomaly_desc="error storm")
    assert result["safe_deployment_hint"] == "dep-safe"


async def test_recall_survives_search_failure(cognee_stub):
    cognee_stub.search = AsyncMock(side_effect=RuntimeError("cognee down"))
    result = await cs.recall(cpu=1, error_rate=1, latency=1, anomaly_desc="x")
    # Degrades gracefully rather than raising.
    assert "No matching incident pattern" in result["answer"]
    assert result["insights"] == []


# ── improve / forget ──────────────────────────────────────────────
async def test_improve(cognee_stub):
    out = await cs.improve()
    assert out["status"] == "ok"
    cognee_stub.cognify.assert_awaited()


async def test_forget(cognee_stub):
    out = await cs.forget("quorum_incidents")
    assert out["status"] == "ok"
    assert out["dataset"] == "quorum_incidents"


# ── setup ─────────────────────────────────────────────────────────
async def test_setup_runs_without_error():
    await cs.setup()  # should not raise even with stubbed cognee config


# ── graph data ────────────────────────────────────────────────────
async def test_get_graph_data_falls_back_to_synthetic_when_empty():
    # No real cognee graph + empty registry -> static fallback graph (non-empty).
    out = await cs.get_graph_data()
    assert out["node_count"] > 0
    assert any(n["group"] == "incident" for n in out["nodes"])


async def test_get_graph_data_synthesises_from_registry():
    await cs.remember_deployment(_dep("dep-a", status="STABLE"))
    await cs.remember_deployment(_dep("dep-b", status="INCIDENT"))
    out = await cs.get_graph_data()
    ids = {n["id"] for n in out["nodes"]}
    assert {"dep-a", "dep-b"} <= ids
    assert any(n["id"] == "dep-b" and n["group"] == "incident" for n in out["nodes"])
    # incident links to the prior stable deployment as its safe state
    assert any(e["source"] == "dep-b" and e["target"] == "dep-a"
               and e["label"] == "rolled back to" for e in out["edges"])


async def test_get_graph_data_builds_nodes_and_edges(monkeypatch):
    raw_nodes = [("dep-1", {"name": "dep-1"}), ("inc-9", {"name": "inc-9"})]
    raw_edges = [("dep-1", "inc-9", {"relationship_name": "caused"})]

    fake_engine = AsyncMock()
    fake_engine.get_graph_data = AsyncMock(return_value=(raw_nodes, raw_edges))
    import cognee.infrastructure.databases.graph as graph_mod
    monkeypatch.setattr(graph_mod, "get_graph_engine",
                        AsyncMock(return_value=fake_engine))

    out = await cs.get_graph_data()
    assert out["node_count"] == 2
    assert out["edge_count"] == 1
    assert out["nodes"][0]["group"] == "deployment"
    assert out["edges"][0]["label"] == "caused"


async def test_get_graph_data_survives_engine_failure(monkeypatch):
    import cognee.infrastructure.databases.graph as graph_mod
    monkeypatch.setattr(graph_mod, "get_graph_engine",
                        AsyncMock(side_effect=RuntimeError("no graph db")))
    out = await cs.get_graph_data()
    # falls back to the synthetic graph instead of crashing
    assert out["node_count"] > 0
