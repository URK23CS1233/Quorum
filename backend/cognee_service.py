"""
Quorum — Cognee Memory Service
"Always knows your last agreed-upon safe state."

Every deployment and incident is ingested into Cognee's hybrid
graph-vector store. When production breaks, Quorum traverses the
graph to recall matching patterns and surface the safe state.
"""

import os
# Silence cognee's PostHog telemetry (otherwise every ingest spams the log with
# eu.i.posthog.com read-timeouts and stalls the request). Must be set before import.
os.environ.setdefault("TELEMETRY_DISABLED", "1")

import cognee
import json
import logging
import pathlib
from typing import Any
from cognee.api.v1.search import SearchType
from models import Deployment, Incident

logger = logging.getLogger(__name__)

# ── Persistent deployment registry ───────────────────────────
# Backed by a JSON file so memory survives backend restarts.
_REGISTRY_FILE = pathlib.Path("quorum_deployments.json")

def _load_registry() -> dict[str, dict]:
    try:
        if _REGISTRY_FILE.exists():
            return json.loads(_REGISTRY_FILE.read_text())
    except Exception as e:
        logger.warning(f"Could not load deployment registry: {e}")
    return {}

def _save_registry(registry: dict[str, dict]):
    try:
        _REGISTRY_FILE.write_text(json.dumps(registry, default=str, indent=2))
    except Exception as e:
        logger.warning(f"Could not save deployment registry: {e}")

# In-memory cache (populated from file on first access)
_deployment_cache: dict[str, Deployment] | None = None
_last_stable_deployment: Deployment | None = None

# Whether Cognee's graph pipeline (LLM entity extraction + embeddings) can run.
# Groq cannot: cognee 0.1.17's cognify has a litellm code path that ignores the
# custom endpoint and 401s against OpenAI. When disabled we skip the graph
# entirely (registry-only) so ingestion stays instant instead of retry-storming.
_graph_enabled: bool = False

def _get_registry() -> dict[str, Deployment]:
    global _deployment_cache
    if _deployment_cache is None:
        raw = _load_registry()
        _deployment_cache = {k: Deployment(**v) for k, v in raw.items()}
    return _deployment_cache


def _use_local_embeddings(model: str, dims: int) -> None:
    """
    Point Cognee at a local Fastembed model instead of the (paid, OpenAI-only)
    default embedding engine. Runs entirely offline after a one-time model
    download — needed because Groq offers no embeddings API. We monkeypatch the
    factory in every module that already imported it by name.
    """
    from cognee.infrastructure.databases.vector.embeddings.FastembedEmbeddingEngine import (
        FastembedEmbeddingEngine,
    )
    engine = FastembedEmbeddingEngine(embedding_model=model, embedding_dimensions=dims)

    def _factory():
        return engine

    import cognee.infrastructure.databases.vector.embeddings.get_embedding_engine as gee_mod
    import cognee.infrastructure.databases.vector.get_vector_engine as gve_mod
    gee_mod.get_embedding_engine = _factory
    gve_mod.get_embedding_engine = _factory


async def setup():
    """Initialise Cognee. Called once at app startup."""
    global _graph_enabled
    import os
    try:
        from cognee.infrastructure.llm.config import get_llm_config
        llm_config = get_llm_config()

        provider = os.getenv("LLM_PROVIDER", "groq")
        model    = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        override = os.getenv("COGNEE_GRAPH", "auto").lower()  # auto | on | off
        llm_config.llm_model = model

        if provider == "groq":
            # Route Groq through the "custom" provider (GenericAPIAdapter honours
            # llm_endpoint) + local Fastembed embeddings. NOTE: cognee 0.1.17's
            # cognify still has a litellm path that ignores the endpoint and 401s
            # against OpenAI, so the graph can't actually build on Groq — we leave
            # it wired but disabled by default (set COGNEE_GRAPH=on to experiment).
            llm_config.llm_provider = "custom"
            llm_config.llm_api_key  = os.getenv("GROQ_API_KEY", "")
            llm_config.llm_endpoint = "https://api.groq.com/openai/v1"
            _use_local_embeddings("BAAI/bge-small-en-v1.5", 384)
            _graph_enabled = (override == "on")
        else:
            # OpenAI (or another provider with a real key) can drive the graph.
            llm_config.llm_provider = "openai"
            llm_config.llm_api_key  = os.getenv("OPENAI_API_KEY", "")
            if os.getenv("EMBEDDING_PROVIDER", "").lower() == "fastembed":
                _use_local_embeddings("BAAI/bge-small-en-v1.5", 384)
            _graph_enabled = override != "off" and bool(llm_config.llm_api_key)

        logger.info(
            f"Quorum memory layer initialised via Cognee ({provider}/{model}) — "
            f"graph {'ENABLED' if _graph_enabled else 'disabled (registry-only)'}"
        )
    except Exception as e:
        logger.warning(f"Cognee config warning (non-fatal): {e}")


# ── remember_deployment ───────────────────────────────────────
async def remember_deployment(dep: Deployment) -> None:
    global _last_stable_deployment
    registry = _get_registry()
    registry[dep.id] = dep
    _save_registry({k: v.dict() for k, v in registry.items()})
    if dep.status == "STABLE":
        _last_stable_deployment = dep

    content = f"""
QUORUM DEPLOYMENT RECORD
========================
Deployment ID : {dep.id}
Timestamp     : {dep.timestamp}
Repository    : {dep.repo or 'production'}
Branch        : {dep.branch}
Commit SHA    : {dep.commit_sha}
Commit Message: {dep.commit_message}
Author        : {dep.author}
Services      : {', '.join(dep.services_affected)}
CPU at deploy : {dep.cpu_at_deploy}%
Error Rate    : {dep.error_rate_at_deploy}%
Latency P99   : {dep.latency_at_deploy}ms
Status        : {dep.status}
""".strip()

    # Graph/vector ingestion is best-effort: the deployment registry above is the
    # source of truth for the UI. Skip it entirely when the graph is disabled so
    # ingestion stays instant (see _graph_enabled / setup()).
    if not _graph_enabled:
        return
    try:
        await cognee.add(content, dataset_name="quorum_deployments")
        await cognee.cognify()
        logger.info(f"Remembered deployment {dep.id} ({dep.commit_sha[:7]})")
    except Exception as e:
        logger.warning(f"Cognee graph ingestion skipped for {dep.id} (registry still updated): {e}")


# ── remember_incident ─────────────────────────────────────────
async def remember_incident(inc: Incident) -> None:
    content = f"""
QUORUM INCIDENT RECORD
======================
Incident ID   : {inc.id}
Severity      : {inc.severity}
Timestamp     : {inc.timestamp}
Triggered by  : {inc.triggered_by_deployment}

Symptoms:
  CPU         : {inc.symptoms.get('cpu', 'N/A')}%
  Error Rate  : {inc.symptoms.get('error_rate', 'N/A')}%
  Latency P99 : {inc.symptoms.get('latency', 'N/A')}ms

Root Cause:
{inc.root_cause}

Resolution:
{inc.resolution}

Safe State Recovery:
  Rolled back to Deployment : {inc.rolled_back_to_deployment}
  Rolled back to Commit     : {inc.rolled_back_to_commit}
  Time to Resolve           : {inc.time_to_resolve_minutes} minutes

LESSON: When symptoms match (high error rate, elevated CPU, latency spike),
the last agreed-upon safe state was {inc.rolled_back_to_deployment}
at commit {inc.rolled_back_to_commit}.
""".strip()

    # Best-effort graph ingestion (see remember_deployment).
    if not _graph_enabled:
        return
    try:
        await cognee.add(content, dataset_name="quorum_incidents")
        await cognee.cognify()
        logger.info(f"Remembered incident {inc.id} → safe state: {inc.rolled_back_to_deployment}")
    except Exception as e:
        logger.warning(f"Cognee graph ingestion skipped for {inc.id}: {e}")


# ── recall ────────────────────────────────────────────────────
async def recall(cpu: float, error_rate: float, latency: float, anomaly_desc: str) -> dict[str, Any]:
    query = (
        f"Production anomaly: CPU {cpu:.1f}%, error rate {error_rate:.2f}%, "
        f"latency {latency:.0f}ms. Anomaly: {anomaly_desc}. "
        f"What caused similar incidents? What was the root cause? "
        f"Which deployment was the last agreed-upon safe state?"
    )

    results: dict[str, Any] = {
        "answer": "", "insights": [], "summaries": [],
        "safe_deployment_hint": None, "safe_commit_hint": None,
    }

    try:
        r = await cognee.search(query, search_type=SearchType.GRAPH_COMPLETION)
        results["answer"] = _extract_text(r)
    except Exception as e:
        logger.warning(f"GRAPH_COMPLETION failed: {e}")
        results["answer"] = "No matching incident pattern found yet. Seed more incident history."

    try:
        r = await cognee.search(query, search_type=SearchType.INSIGHTS)
        results["insights"] = _extract_insights(r)
    except Exception as e:
        logger.warning(f"INSIGHTS failed: {e}")

    try:
        r = await cognee.search(query, search_type=SearchType.SUMMARIES)
        results["summaries"] = _extract_summaries(r)
    except Exception as e:
        logger.warning(f"SUMMARIES failed: {e}")

    for dep_id, dep in _get_registry().items():
        if dep_id in results["answer"] or dep.commit_sha[:7] in results["answer"]:
            if dep.status == "STABLE":
                results["safe_deployment_hint"] = dep_id
                results["safe_commit_hint"] = dep.commit_sha

    return results


# ── improve ───────────────────────────────────────────────────
async def improve() -> dict:
    await cognee.cognify()
    return {"status": "ok", "message": "Quorum memory graph strengthened."}


# ── forget ────────────────────────────────────────────────────
async def forget(dataset: str = "quorum_incidents") -> dict:
    await cognee.prune.prune_data()
    return {"status": "ok", "dataset": dataset}


# ── graph data ────────────────────────────────────────────────
async def get_graph_data() -> dict:
    # Prefer the real Cognee graph when it actually built (needs a graph-capable LLM).
    try:
        from cognee.infrastructure.databases.graph import get_graph_engine
        engine = await get_graph_engine()
        raw = await engine.get_graph_data()
        nodes, edges = [], []
        if isinstance(raw, tuple) and len(raw) == 2:
            raw_nodes, raw_edges = raw
            for node_id, attrs in (raw_nodes or []):
                label = _node_label(attrs)
                nodes.append({"id": str(node_id), "label": label, "group": _node_group(label, attrs)})
            for src, tgt, attrs in (raw_edges or []):
                edges.append({
                    "source": str(src), "target": str(tgt),
                    "label": attrs.get("relationship_name", "related") if isinstance(attrs, dict) else "related"
                })
        if nodes:
            return {"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}
    except Exception as e:
        logger.warning(f"Graph extraction failed: {e}")
    # Cognee graph is empty (e.g. Groq can't run the graph pipeline) — synthesise a
    # knowledge graph from the deployment registry so the view is still populated.
    return _synthetic_graph_from_registry()


def _synthetic_graph_from_registry(limit: int = 14) -> dict:
    """
    Derive a Knowledge Graph from the deployment registry. Each deployment links to
    the engineer who shipped it, its commit, and the services it touched; an
    INCIDENT deployment also links to the last stable state it was rolled back to.
    Shared services/authors weave the deployments into one connected graph.
    """
    deployments = get_all_deployments()[-limit:]
    if not deployments:
        return _HARDCODED_GRAPH

    nodes: list[dict] = []
    edges: list[dict] = []
    seen: set[str] = set()

    def node(nid: str, label: str, group: str):
        if nid not in seen:
            seen.add(nid)
            nodes.append({"id": nid, "label": label, "group": group})

    for i, d in enumerate(deployments):
        is_incident = d.status == "INCIDENT"
        node(d.id, d.id, "incident" if is_incident else "deployment")

        pid = f"person::{d.author}"
        node(pid, d.author, "person")
        edges.append({"source": pid, "target": d.id, "label": "deployed"})

        cid = f"commit::{d.commit_sha[:7]}"
        node(cid, d.commit_sha[:7], "commit")
        edges.append({"source": d.id, "target": cid, "label": "commit"})

        for svc in d.services_affected[:3]:
            sid = f"svc::{svc}"
            node(sid, svc, "service")
            edges.append({"source": d.id, "target": sid, "label": "affects"})

        if is_incident:
            # nearest prior STABLE deployment = the safe state to roll back to
            for prior in reversed(deployments[:i]):
                if prior.status == "STABLE":
                    edges.append({"source": d.id, "target": prior.id, "label": "rolled back to"})
                    break

    return {"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}


# Static fallback used only when the registry is empty.
_HARDCODED_GRAPH = {
    "nodes": [
        {"id": "dep-002", "label": "dep-002", "group": "incident"},
        {"id": "dep-001", "label": "dep-001", "group": "deployment"},
        {"id": "svc::payment-service", "label": "payment-service", "group": "service"},
        {"id": "svc::queue-worker", "label": "queue-worker", "group": "service"},
        {"id": "person::Sarah Chen", "label": "Sarah Chen", "group": "person"},
        {"id": "cause::oom", "label": "queue OOM", "group": "cause"},
        {"id": "res::rollback", "label": "rollback to dep-001", "group": "resolution"},
    ],
    "edges": [
        {"source": "person::Sarah Chen", "target": "dep-002", "label": "deployed"},
        {"source": "dep-002", "target": "svc::payment-service", "label": "affects"},
        {"source": "dep-002", "target": "svc::queue-worker", "label": "affects"},
        {"source": "dep-002", "target": "cause::oom", "label": "root cause"},
        {"source": "dep-002", "target": "res::rollback", "label": "resolved by"},
        {"source": "dep-002", "target": "dep-001", "label": "rolled back to"},
    ],
    "node_count": 7, "edge_count": 6,
}


# ── registry helpers ──────────────────────────────────────────
def get_last_stable_deployment() -> Deployment | None:
    return _last_stable_deployment

def get_deployment(dep_id: str) -> Deployment | None:
    return _get_registry().get(dep_id)

def get_all_deployments() -> list[Deployment]:
    return list(_get_registry().values())


# ── internals ─────────────────────────────────────────────────
def _extract_text(result: Any) -> str:
    if not result:
        return ""
    if isinstance(result, list):
        parts = []
        for r in result[:3]:
            t = r.get("text") or r.get("answer") or r.get("content") if isinstance(r, dict) else str(r)
            if t:
                parts.append(t)
        return "\n\n".join(parts)
    return str(result)

def _extract_insights(result: Any) -> list[dict]:
    out = []
    for r in (result if isinstance(result, list) else [result])[:6]:
        if isinstance(r, dict):
            out.append({
                "subject": _safe_name(r.get("node")),
                "relationship": r.get("relationship", "related to"),
                "object": _safe_name(r.get("neighbor")),
            })
    return out

def _extract_summaries(result: Any) -> list[str]:
    out = []
    for r in (result if isinstance(result, list) else [result])[:3]:
        t = r.get("text") or r.get("summary") if isinstance(r, dict) else str(r)
        if t:
            out.append(t)
    return out

def _safe_name(obj: Any) -> str:
    if isinstance(obj, dict):
        return obj.get("name") or obj.get("label") or str(obj)[:30]
    return str(obj)[:30] if obj else ""

def _node_label(attrs: Any) -> str:
    if isinstance(attrs, dict):
        return attrs.get("name") or attrs.get("label") or attrs.get("id", "node")
    return str(attrs)[:25]

def _node_group(label: str, attrs: Any) -> str:
    l = label.lower()
    t = (attrs.get("type", "") if isinstance(attrs, dict) else "").lower()
    if "dep-" in l or "deploy" in l:   return "deployment"
    if "inc-" in l or "incident" in l: return "incident"
    if "commit" in l or "sha" in l:    return "commit"
    if "service" in l or "api" in l:   return "service"
    if "person" in t or "@" in l:      return "person"
    if "root" in l or "cause" in l:    return "cause"
    if "resolv" in l or "fix" in l:    return "resolution"
    return "concept"
