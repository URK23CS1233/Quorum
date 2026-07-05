"""
Production Incident Memory with Cognee
=======================================
Demonstrates how to use Cognee as the memory layer for a production
incident-prevention system.

The pattern:
  1. Ingest deployment records as structured text → Cognee builds a graph
  2. Ingest incident post-mortems linking incidents to their root deployments
  3. At alert time, query Cognee to recall which deployment caused similar
     symptoms and what the last agreed-upon safe state was

This is useful for on-call engineers who need instant causal context:
"We've seen this CPU spike + error rate pattern before — here's what caused
it and which commit to roll back to."

Requirements:
    pip install cognee python-dotenv

Usage:
    # Set your LLM API key (supports OpenAI, Groq, Anthropic, Ollama, …)
    export OPENAI_API_KEY=sk-...   # or GROQ_API_KEY, etc.
    python example.py
"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import cognee
from cognee.api.v1.search import SearchType


# ── Data models ───────────────────────────────────────────────

@dataclass
class Deployment:
    id: str
    commit_sha: str
    commit_message: str
    author: str
    branch: str
    services: list[str]
    status: str = "STABLE"          # STABLE | DEGRADED | ROLLED_BACK
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class Incident:
    id: str
    triggered_by: str               # deployment id
    root_cause: str
    resolution: str
    rolled_back_to: str             # deployment id of safe state
    rolled_back_commit: str
    severity: str = "P1"
    ttm_minutes: int = 0            # time-to-mitigate
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── Memory helpers ────────────────────────────────────────────

def _deployment_to_text(d: Deployment) -> str:
    return f"""
DEPLOYMENT RECORD
=================
ID            : {d.id}
Timestamp     : {d.timestamp}
Branch        : {d.branch}
Commit SHA    : {d.commit_sha}
Commit Message: {d.commit_message}
Author        : {d.author}
Services      : {', '.join(d.services)}
Status        : {d.status}
""".strip()


def _incident_to_text(i: Incident) -> str:
    return f"""
INCIDENT POST-MORTEM
====================
ID              : {i.id}
Severity        : {i.severity}
Timestamp       : {i.timestamp}
Triggered By    : deployment {i.triggered_by}
Root Cause      : {i.root_cause}
Resolution      : {i.resolution}
Safe Rollback   : deployment {i.rolled_back_to} (commit {i.rolled_back_commit})
Time to Mitigate: {i.ttm_minutes} minutes

LESSON LEARNED: When symptoms match this root cause, roll back to
deployment {i.rolled_back_to} at commit {i.rolled_back_commit}.
""".strip()


async def remember_deployment(dep: Deployment) -> None:
    """Ingest a deployment record into Cognee's graph-vector memory."""
    await cognee.add(_deployment_to_text(dep), dataset_name="deployments")
    await cognee.cognify()
    print(f"  ✓ Remembered deployment {dep.id} ({dep.commit_sha[:7]})")


async def remember_incident(inc: Incident) -> None:
    """Ingest an incident post-mortem so future alerts can learn from it."""
    await cognee.add(_incident_to_text(inc), dataset_name="incidents")
    await cognee.cognify()
    print(f"  ✓ Remembered incident {inc.id} (caused by {inc.triggered_by})")


async def recall_safe_state(
    symptom_description: str,
    cpu_pct: float = 0.0,
    error_rate_pct: float = 0.0,
    latency_ms: float = 0.0,
) -> dict:
    """
    Given current production symptoms, query Cognee to surface:
    - Which past deployment caused similar issues
    - What the root cause was
    - Which deployment to roll back to
    """
    query = (
        f"Production alert — CPU {cpu_pct:.0f}%, "
        f"error rate {error_rate_pct:.1f}%, latency {latency_ms:.0f}ms. "
        f"Symptom: {symptom_description}. "
        f"What deployment caused similar incidents before? "
        f"What was the root cause? "
        f"Which deployment is the last agreed-upon safe state to roll back to?"
    )

    result = {"answer": "", "insights": [], "safe_state_hint": None}

    # Graph traversal — finds causal chains between deployments and incidents
    try:
        r = await cognee.search(query, search_type=SearchType.GRAPH_COMPLETION)
        if r:
            chunks = [
                (item.get("text") or item.get("answer") or str(item))
                for item in (r if isinstance(r, list) else [r])
            ]
            result["answer"] = "\n\n".join(c for c in chunks[:3] if c)
    except Exception as e:
        print(f"  ⚠ GRAPH_COMPLETION: {e}")

    # Entity relationships — surfaces deployment → incident links
    try:
        r = await cognee.search(query, search_type=SearchType.INSIGHTS)
        if r:
            result["insights"] = [
                {
                    "subject":      item.get("node", {}).get("name", ""),
                    "relationship": item.get("relationship", "related to"),
                    "object":       item.get("neighbor", {}).get("name", ""),
                }
                for item in (r if isinstance(r, list) else [r])
                if isinstance(item, dict)
            ][:6]
    except Exception as e:
        print(f"  ⚠ INSIGHTS: {e}")

    return result


# ── Demo ──────────────────────────────────────────────────────

async def main() -> None:
    print("\n🔒 Cognee Production Incident Memory — Demo\n")

    # ── Phase 1: Seed deployment history ──────────────────────
    print("Phase 1: Ingesting deployment history into Cognee…")

    deployments = [
        Deployment(
            id="dep-001",
            commit_sha="a1b2c3d4e5f6",
            commit_message="Add Redis caching layer to user-service",
            author="alice@example.com",
            branch="main",
            services=["user-service", "cache"],
            status="STABLE",
        ),
        Deployment(
            id="dep-002",
            commit_sha="b2c3d4e5f6a7",
            commit_message="Migrate auth-service to async database driver",
            author="bob@example.com",
            branch="main",
            services=["auth-service", "postgres"],
            status="ROLLED_BACK",
        ),
        Deployment(
            id="dep-003",
            commit_sha="c3d4e5f6a7b8",
            commit_message="Optimise payment-service query with composite index",
            author="carol@example.com",
            branch="main",
            services=["payment-service", "postgres"],
            status="STABLE",
        ),
    ]

    for dep in deployments:
        await remember_deployment(dep)

    # ── Phase 2: Seed incident post-mortems ───────────────────
    print("\nPhase 2: Ingesting incident post-mortems into Cognee…")

    incidents = [
        Incident(
            id="inc-001",
            triggered_by="dep-002",
            root_cause=(
                "The async database driver in auth-service opened unbounded "
                "connection pools under load, exhausting Postgres connections. "
                "This caused auth-service to return 502 errors, cascading to "
                "all services that depend on authentication."
            ),
            resolution=(
                "Rolled back auth-service to dep-001. Added connection pool "
                "limits (max_connections=20) to the async driver config."
            ),
            rolled_back_to="dep-001",
            rolled_back_commit="a1b2c3d4e5f6",
            severity="P1",
            ttm_minutes=23,
        ),
    ]

    for inc in incidents:
        await remember_incident(inc)

    # ── Phase 3: Simulate a production alert ──────────────────
    print("\nPhase 3: Production alert triggered — querying Cognee memory…")
    print("  Symptoms: CPU 78%, error rate 12.4%, latency 2300ms")
    print("  Alert: auth-service returning 502 errors\n")

    result = await recall_safe_state(
        symptom_description="auth-service returning 502 errors, Postgres connection timeouts in logs",
        cpu_pct=78,
        error_rate_pct=12.4,
        latency_ms=2300,
    )

    print("=" * 60)
    print("COGNEE MEMORY RECALL")
    print("=" * 60)

    if result["answer"]:
        print("\n📋 Causal Analysis:")
        print(result["answer"])
    else:
        print("\n⚠  No matching memory found. Seed more incident history.")

    if result["insights"]:
        print("\n🔗 Graph Relationships:")
        for ins in result["insights"]:
            if ins.get("subject") and ins.get("object"):
                print(f"  {ins['subject']} → {ins['relationship']} → {ins['object']}")

    print("\n" + "=" * 60)
    print("✅ Demo complete.")
    print(
        "\nNext steps: integrate this pattern into your incident-response "
        "workflow. Every post-mortem you ingest makes the next alert smarter."
    )


if __name__ == "__main__":
    # Configure your LLM provider via environment variables.
    # Cognee supports OpenAI, Groq, Anthropic, Azure OpenAI, Ollama, and more.
    # See: https://docs.cognee.ai/getting-started/configuration
    asyncio.run(main())
