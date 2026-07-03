# How I Built a Production Incident AI That Actually Remembers — Using Cognee Graph Memory

*Built for the WeMakeDevs × Cognee "Where's My Context?" Hackathon*

---

## The 2am Problem

Every engineer knows the feeling. Production is down. Error rate is climbing. Slack is on fire. And you're frantically asking the same questions:

- What changed in the last deploy?
- Has this happened before?
- **Which commit do I roll back to?**

The answer exists somewhere — in a postmortem doc, a Slack thread, a colleague's memory. But by the time you find it, 45 minutes have passed and your SLA is in ruins.

I built **Quorum** to solve this. And the reason it works is Cognee.

---

## Why Graph Memory Changes Everything

My first instinct was to build a RAG system. Store all incidents as embeddings, query for similar ones when a new incident fires. Standard stuff.

Then I thought about the actual question I needed to answer:

> *"Given this error storm on the payment-service, what deployment do I roll back to?"*

A vector search would find semantically similar incidents — incidents that used the same words. But what I actually need is to traverse a **causal chain**:

```
error_storm anomaly
    → matches past incident #inc-001
    → root cause: multi-currency integer overflow
    → caused by deployment dep-002 (a3f8c12)
    → safe state: deployment dep-001 (7d2e891)
```

That's not similarity. That's a directed graph traversal. And that's exactly what `SearchType.GRAPH_COMPLETION` in Cognee does.

---

## The Architecture

Quorum has three layers:

**1. Memory Layer (Cognee)**
Every deployment and incident is ingested into Cognee's hybrid graph-vector store:

```python
await cognee.add(deployment_text, dataset_name="production")
await cognee.cognify()  # builds the knowledge graph
```

`cognify()` doesn't just embed text — it extracts entities and relationships, building a graph where deployments connect to services, incidents connect to root causes, and rollbacks connect to safe states.

**2. Recall Layer (Three Search Types)**
When an anomaly fires, Quorum queries Cognee three ways:

```python
# The core — causal chain traversal
graph_answer = await cognee.search(
    SearchType.GRAPH_COMPLETION,
    query="safe rollback for error_storm on payment-service"
)

# Entity relationships for visualization  
insights = await cognee.search(SearchType.INSIGHTS, query=anomaly)

# Context for the AI assistant
summary = await cognee.search(SearchType.SUMMARIES, query=anomaly)
```

**3. Application Layer (FastAPI + Next.js)**
- Live WebSocket metrics streaming with anomaly detection
- Cinematic Next.js 14 dashboard with real-time incident panel
- JWT auth with 5 RBAC roles (SUPER_ADMIN → VIEWER)
- Multi-source ingestion: GitHub, PagerDuty, Datadog
- AI chat assistant where context persists across sessions (re-ingested into Cognee after every exchange)

---

## The Aha Moment

The moment that made me really understand Cognee's power: I seeded the system with a past payment-service incident, ran a new error storm simulation, and queried GRAPH_COMPLETION.

It came back with the exact deployment SHA, the root cause, and the author of the bad commit — **from a graph traversal, not from LLM reasoning**. The LLM never saw the raw incident data. Cognee's graph had already connected the dots.

That's the difference between "your AI knows things" and "your AI remembers things."

---

## What I'd Do Next (The Product Roadmap)

Quorum is genuinely useful. Here's what it needs to become a real SaaS:

1. **Cognee Cloud** — replace SQLite with hosted Cognee for multi-tenant isolation
2. **Webhook ingestion** — GitHub, PagerDuty, and Datadog push directly to Quorum in real time
3. **Runbook generation** — after each incident, Cognee generates a postmortem + runbook from memory
4. **Slack bot** — `/quorum rollback` from Slack, answer in thread
5. **Pricing** — $49/seat for ANALYST+, $299/team (≤10), Enterprise custom

The market is real: Incident.io raised $45M, PagerDuty is at $600M ARR, and neither of them has an AI with actual memory of your past incidents.

---

## Key Learnings

- **Graph traversal ≠ vector search** — GRAPH_COMPLETION is for causal questions, not similarity questions. Use the right tool.
- **Memory namespacing matters** — isolating per-user vs. per-org Cognee datasets is the difference between a personal assistant and a team brain.
- **`cognify()` is not instant** — in production, run it in a background task after ingestion. Don't block the API response.
- **The UI matters for AI tools** — engineers won't trust a rollback recommendation from a plain JSON response. Confidence scores, graph visualizations, and audit logs make AI actions feel safe.

---

## Links

- **GitHub**: https://github.com/jeffychristaj/quorum
- **Live demo**: https://quorum-demo.vercel.app
- **Cognee**: https://github.com/topoteretes/cognee

*Built for the WeMakeDevs × Cognee "Where's My Context?" Hackathon, July 2026.*
*AI disclosure: Claude (Anthropic) was used as a coding assistant for boilerplate. Architecture, Cognee integration, and core logic designed by the developer.*

