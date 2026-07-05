# Production Incident Memory

This example shows how to use Cognee as the memory layer for a **production
incident-prevention system** — a pattern where every deployment and incident
post-mortem is ingested into Cognee's graph-vector store so that when the
next alert fires, on-call engineers get instant causal context.

## The Problem

When production breaks at 3 AM, engineers waste the first 20 minutes asking:
- "Have we seen this before?"
- "Which deployment caused it?"
- "What did we roll back to last time?"

The answers exist in Slack threads, post-mortems, and runbooks — but nobody
can find them under pressure.

## The Solution

Use Cognee to build a **causal memory graph** from your deployment history
and incident post-mortems. When an alert fires, query Cognee with the current
symptoms and it traverses the graph to surface:

- Which past deployment caused the same pattern
- The root cause from the post-mortem
- The exact commit that was the last safe rollback target

## How It Works

```
Ingest phase (happens continuously):
  deployment record → cognee.add() → cognee.cognify() → graph + vectors

Alert phase (happens at incident time):
  symptoms → cognee.search(GRAPH_COMPLETION) → causal chain recall
           → cognee.search(INSIGHTS)         → entity relationships
```

Cognee builds a knowledge graph linking deployments → incidents → root causes
→ safe states. The `GRAPH_COMPLETION` search traverses this graph to answer
natural-language questions about your system's history.

## Setup

```bash
pip install cognee python-dotenv
```

Set your LLM provider (Cognee supports OpenAI, Groq, Anthropic, Azure, Ollama):

```bash
# Option A — OpenAI
export OPENAI_API_KEY=sk-...

# Option B — Groq (free tier available at console.groq.com)
export LLM_API_KEY=gsk_...
export LLM_PROVIDER=groq
export LLM_MODEL=llama-3.3-70b-versatile

# Option C — Ollama (fully local, no API key needed)
export LLM_PROVIDER=ollama
export LLM_MODEL=llama3.2
```

## Run

```bash
python example.py
```

Expected output:

```
🔒 Cognee Production Incident Memory — Demo

Phase 1: Ingesting deployment history into Cognee…
  ✓ Remembered deployment dep-001 (a1b2c3)
  ✓ Remembered deployment dep-002 (b2c3d4)
  ✓ Remembered deployment dep-003 (c3d4e5)

Phase 2: Ingesting incident post-mortems into Cognee…
  ✓ Remembered incident inc-001 (caused by dep-002)

Phase 3: Production alert triggered — querying Cognee memory…
  Symptoms: CPU 78%, error rate 12.4%, latency 2300ms
  Alert: auth-service returning 502 errors

============================================================
COGNEE MEMORY RECALL
============================================================

📋 Causal Analysis:
Deployment dep-002 (async database driver migration) previously caused
identical symptoms: auth-service 502 errors due to unbounded Postgres
connection pools. The last safe state is dep-001 at commit a1b2c3d4e5f6.

🔗 Graph Relationships:
  dep-002 → caused → inc-001
  inc-001 → resolved by rollback to → dep-001
  dep-001 → is safe state for → auth-service
```

## Extending This Example

**Add more incident types:**
```python
await remember_incident(Incident(
    id="inc-002",
    triggered_by="dep-005",
    root_cause="N+1 query in payment-service after ORM migration",
    resolution="Added select_related() calls, rolled back to dep-003",
    rolled_back_to="dep-003",
    rolled_back_commit="c3d4e5f6a7b8",
))
```

**Query with richer context:**
```python
result = await recall_safe_state(
    symptom_description="payment timeouts, Postgres CPU at 95%",
    cpu_pct=91,
    error_rate_pct=8.2,
    latency_ms=5400,
)
```

**Integrate with your alerting pipeline:**
Connect `recall_safe_state()` to PagerDuty, Grafana alerts, or any webhook
so every alert automatically includes Cognee's causal memory in the
notification body.

## Real-World Project

This example is distilled from **Quorum**, a production incident-prevention
platform built for the WeMakeDevs × Cognee hackathon (2026). Quorum wraps
this pattern in a full-stack application with a live metrics dashboard,
WebSocket streaming, RBAC, and a chat interface for querying incident memory
in natural language.

→ [github.com/URK23CS1233/Quorum](https://github.com/URK23CS1233/Quorum)

## Key Cognee APIs Used

| API | Purpose |
|-----|---------|
| `cognee.add(text, dataset_name=...)` | Ingest deployment/incident records |
| `cognee.cognify()` | Build graph relationships from ingested text |
| `cognee.search(query, SearchType.GRAPH_COMPLETION)` | Causal chain recall |
| `cognee.search(query, SearchType.INSIGHTS)` | Entity relationship extraction |
