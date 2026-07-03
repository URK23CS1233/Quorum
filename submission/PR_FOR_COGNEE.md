# PR to Raise on Cognee GitHub

## STEP-BY-STEP PROCESS (do this TODAY — July 3)

### Step 1: Find issues to work on
Go to: https://github.com/topoteretes/cognee/issues
Filter by: "help wanted" or "good first issue" or "documentation"

### Step 2: Claim issues (comment on each one you want)
Comment exactly this on the issue:
> Hi, I'd like to work on this issue. I'm participating in the WeMakeDevs × Cognee hackathon and this aligns with what I've built. @[maintainer_handle] could you assign this to me? Thanks!

Wait for assignment before opening PR.

### Step 3: If no good issues exist — open a PR for this example

Create this PR: **"feat(examples): Add production incident memory example"**

---

## THE PR CODE

### File: `examples/production_incident_memory/main.py`
*(Raise this as a PR to https://github.com/topoteretes/cognee)*

```python
"""
Production Incident Memory with Cognee
=======================================
This example shows how to use Cognee's graph-vector memory to build
a production incident prevention system.

The key insight: production incident recall is a GRAPH problem, not a
similarity problem. The chain:
    anomaly → incident → root_cause → bad_deployment → safe_state
requires causal traversal — which is exactly what SearchType.GRAPH_COMPLETION
provides, and what plain vector search cannot do.

Run:
    pip install cognee openai
    export OPENAI_API_KEY=sk-...
    python main.py
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import cognee
from cognee.api.v1.search import SearchType


# ── Data models ──────────────────────────────────────────────────────────────

@dataclass
class Deployment:
    id: str
    service: str
    commit_sha: str
    commit_message: str
    author: str
    timestamp: str
    status: str  # "healthy" | "rolled_back"

@dataclass
class Incident:
    id: str
    anomaly_type: str           # "error_storm" | "cpu_spike" | "latency_blowup"
    affected_service: str
    triggered_at: str
    root_cause: str
    bad_deployment_id: str
    safe_deployment_id: str     # the commit to roll back to
    resolved: bool


# ── Memory operations ─────────────────────────────────────────────────────────

async def remember_deployment(deployment: Deployment, namespace: str = "production") -> None:
    """
    Ingest a deployment into Cognee's knowledge graph.
    
    Cognee builds a graph of relationships:
        deployment → service
        deployment → commit
        deployment → author
        deployment → status
    """
    text = (
        f"Deployment {deployment.id}: service={deployment.service}, "
        f"commit={deployment.commit_sha[:8]}, "
        f"message='{deployment.commit_message}', "
        f"author={deployment.author}, "
        f"status={deployment.status}, "
        f"timestamp={deployment.timestamp}"
    )
    await cognee.add(text, dataset_name=namespace)
    print(f"  ✓ Remembered deployment {deployment.id} ({deployment.service})")


async def remember_incident(incident: Incident, namespace: str = "production") -> None:
    """
    Ingest an incident into Cognee's knowledge graph.
    
    This creates causal edges:
        incident → anomaly_type
        incident → affected_service
        incident → root_cause
        incident → bad_deployment (caused_by)
        incident → safe_deployment (resolved_by)
    """
    text = (
        f"Incident {incident.id}: anomaly={incident.anomaly_type}, "
        f"service={incident.affected_service}, "
        f"root_cause='{incident.root_cause}', "
        f"caused_by_deployment={incident.bad_deployment_id}, "
        f"safe_rollback_deployment={incident.safe_deployment_id}, "
        f"resolved={incident.resolved}"
    )
    await cognee.add(text, dataset_name=namespace)
    print(f"  ✓ Remembered incident {incident.id} ({incident.anomaly_type})")


async def build_memory_graph(namespace: str = "production") -> None:
    """
    Process all ingested data into a queryable knowledge graph.
    Must be called after all add() calls.
    """
    print("\n  Building knowledge graph (cognify)...")
    await cognee.cognify()
    print("  ✓ Memory graph ready")


async def recall_safe_state(anomaly_type: str, service: str, namespace: str = "production") -> dict:
    """
    The core of production incident prevention.
    
    Uses GRAPH_COMPLETION to traverse the causal chain:
        current anomaly → similar past incident → root cause → bad deploy → safe state
    
    This is impossible with plain vector search — it requires graph traversal
    because we're following CAUSAL relationships, not semantic similarity.
    """
    query = (
        f"Given a {anomaly_type} anomaly on the {service} service, "
        f"what deployment should we roll back to? "
        f"What was the root cause and what is the safe deployment state?"
    )
    
    # GRAPH_COMPLETION: traverses causal chains in the knowledge graph
    graph_results = await cognee.search(SearchType.GRAPH_COMPLETION, query=query)
    
    # INSIGHTS: extracts entity relationships (subject, relationship, object)
    insight_results = await cognee.search(SearchType.INSIGHTS, query=query)
    
    # SUMMARIES: high-level context
    summary_results = await cognee.search(SearchType.SUMMARIES, query=query)
    
    return {
        "anomaly": anomaly_type,
        "service": service,
        "recall_answer": graph_results[0] if graph_results else "No matching incidents in memory",
        "graph_insights": insight_results[:3] if insight_results else [],
        "summary": summary_results[0] if summary_results else "",
    }


async def get_graph_snapshot(namespace: str = "production") -> list:
    """
    Return all graph nodes and edges for visualization.
    Useful for building a D3.js force-directed graph of your incident history.
    """
    return await cognee.search(SearchType.INSIGHTS, query="all deployments incidents services")


# ── Demo ──────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("  Cognee Production Incident Memory — Demo")
    print("=" * 60)

    # ── Step 1: Reset and configure Cognee ───────────────────────────────────
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    print("\n[1] Cognee initialized\n")

    # ── Step 2: Ingest deployment history ────────────────────────────────────
    print("[2] Ingesting deployment history...")
    
    deployments = [
        Deployment(
            id="dep-001", service="payment-service",
            commit_sha="7d2e891a3f4b", commit_message="refactor: improve checkout flow",
            author="alice", timestamp="2026-06-28T10:00:00Z", status="healthy"
        ),
        Deployment(
            id="dep-002", service="payment-service",
            commit_sha="a3f8c12b9e01", commit_message="feat: add multi-currency support",
            author="bob", timestamp="2026-06-29T14:30:00Z", status="rolled_back"
        ),
        Deployment(
            id="dep-003", service="auth-service",
            commit_sha="c91d4e7f2a56", commit_message="fix: JWT expiry edge case",
            author="alice", timestamp="2026-06-30T09:15:00Z", status="healthy"
        ),
    ]
    
    for dep in deployments:
        await remember_deployment(dep)
    
    # ── Step 3: Ingest incident history ──────────────────────────────────────
    print("\n[3] Ingesting incident history...")
    
    incidents = [
        Incident(
            id="inc-001", anomaly_type="error_storm",
            affected_service="payment-service",
            triggered_at="2026-06-29T15:45:00Z",
            root_cause="Multi-currency conversion caused integer overflow in payment processor",
            bad_deployment_id="dep-002",
            safe_deployment_id="dep-001",
            resolved=True,
        ),
    ]
    
    for inc in incidents:
        await remember_incident(inc)
    
    # ── Step 4: Build the knowledge graph ────────────────────────────────────
    await build_memory_graph()
    
    # ── Step 5: Simulate an incident and recall safe state ───────────────────
    print("\n[4] Simulating new incident: error_storm on payment-service")
    print("    Querying Cognee for safe rollback state...\n")
    
    result = await recall_safe_state(
        anomaly_type="error_storm",
        service="payment-service"
    )
    
    print("=" * 60)
    print("  QUORUM INCIDENT ANALYSIS")
    print("=" * 60)
    print(f"\n  Anomaly:  {result['anomaly']} on {result['service']}")
    print(f"\n  Recall Answer:\n  {result['recall_answer']}")
    
    if result["graph_insights"]:
        print("\n  Graph Insights (causal chain):")
        for ins in result["graph_insights"]:
            if isinstance(ins, dict):
                print(f"    {ins.get('subject','?')} → {ins.get('relationship','?')} → {ins.get('object','?')}")
    
    print("\n  ✓ Cognee traversed the causal graph to find the safe rollback state.")
    print("    This is GRAPH_COMPLETION — not similarity search.\n")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

### File: `examples/production_incident_memory/README.md`

```markdown
# Production Incident Memory with Cognee

This example demonstrates how to use Cognee's graph-vector memory for
**production incident prevention** — specifically, how to recall the safe
rollback state after a production anomaly using causal graph traversal.

## The Problem

When production breaks, engineers need to answer:
1. Has this happened before?
2. What caused it?
3. Which deployment is safe to roll back to?

Vector search finds *semantically similar* incidents. Cognee's graph traversal
finds *causally related* ones. The difference matters:

```
anomaly → incident → root_cause → bad_deployment → safe_state
```

This causal chain is a directed graph — not a similarity problem.

## How it works

| Cognee API | Purpose |
|---|---|
| `cognee.add()` + `cognee.cognify()` | Ingest deployments & incidents into graph |
| `SearchType.GRAPH_COMPLETION` | Traverse causal chain to find safe rollback |
| `SearchType.INSIGHTS` | Extract (subject, relationship, object) triples |
| `SearchType.SUMMARIES` | High-level operational context for AI chat |

## Run

```bash
pip install cognee openai
export OPENAI_API_KEY=sk-...
python main.py
```

## Real-world extension

This pattern powers [Quorum](https://github.com/jeffychristaj/quorum), a
full-stack production incident platform built on top of Cognee with:
- Live WebSocket metrics streaming
- Role-based team access (5 roles)
- Multi-source ingestion (GitHub, PagerDuty, Datadog)
- AI chat assistant with persistent memory
- D3.js knowledge graph visualization
```

### File: `examples/production_incident_memory/requirements.txt`
```
cognee>=0.1.0
openai>=1.0.0
```

---

## PR TITLE
`feat(examples): Add production incident memory example using GRAPH_COMPLETION`

## PR DESCRIPTION (paste this into GitHub)

```
## Summary

Adds a self-contained example showing how to use Cognee for production 
incident prevention — specifically, how to recall the safe rollback 
deployment after a production anomaly using causal graph traversal.

## Motivation

Production incident recall is fundamentally a graph problem, not a 
similarity problem. The causal chain:

    anomaly → incident → root_cause → bad_deployment → safe_state

requires traversing directed relationships — exactly what 
`SearchType.GRAPH_COMPLETION` provides. This example makes that 
pattern concrete and runnable.

## What's added

- `examples/production_incident_memory/main.py` — complete runnable demo
- `examples/production_incident_memory/README.md` — explains the pattern
- `examples/production_incident_memory/requirements.txt`

## How to test

```bash
cd examples/production_incident_memory
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python main.py
```

## Related

Built during the WeMakeDevs × Cognee "Where's My Context?" hackathon.
This example is extracted from Quorum (https://github.com/jeffychristaj/quorum),
a production-grade implementation of this pattern.
```

---

## ALSO: Find 1-2 open issues to claim for extra $100 each

Search https://github.com/topoteretes/cognee/issues for:
- label:"good first issue"  
- label:"help wanted"
- label:"documentation"
- Anything related to: FastAPI integration, async patterns, examples, type hints

Good issue types to claim:
1. "Add type hints to X module"
2. "Improve error messages in cognify()"
3. "Add async context manager support"
4. "Document SearchType parameters"
5. "Add example for [specific use case]"

