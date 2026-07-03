# Quorum — Hackathon Submission Package
## "Where's My Context?" · WeMakeDevs × Cognee · July 5, 2026

---

## SECTION 1: FORM ANSWERS (copy-paste ready)

### Email
jeffychristaj@gmail.com

### Team name
Jeffy Edwina Christa

### Name of the person submitting the form
Jeffy Edwina Christa

### Track
✅ Track 1: Best Use of Cognee Open Source

---

### Project description

**Quorum** — *"Always knows your last agreed-upon safe state."*

Quorum is a production incident prevention platform that gives engineering teams instant AI-powered recall of their last safe deployment state. When production breaks — CPU spikes, error rates climb, latency explodes — Quorum already knows the fix before an on-call engineer has opened their laptop.

Traditional incident tools (PagerDuty, Datadog) tell you *that* something broke. Quorum tells you *why*, and *exactly which commit to roll back to*, by traversing a living knowledge graph of every deployment, incident, and rollback your team has ever done.

**Key capabilities:**
- **Live anomaly detection** — WebSocket streaming of CPU, error rate, latency P99, and memory. Threshold breaches trigger Cognee recall instantly
- **Causal chain traversal** — Cognee's GRAPH_COMPLETION follows the path: anomaly → incident → root cause → bad deployment → safe state
- **AI assistant with persistent memory** — ask "What broke last Tuesday?" and get a precise answer from Cognee's graph, not an LLM hallucination
- **Role-based team access** — SUPER_ADMIN, ADMIN, OPERATOR, ANALYST, VIEWER with both API and UI enforcement
- **Multi-source ingestion** — GitHub commits, PagerDuty incidents, Datadog metrics, Slack alerts — all flow into Cognee memory
- **Full production UI** — Next.js 14 dark-mode dashboard with cinematic animations, auth, and D3.js knowledge graph visualization

**Stack:** Cognee · FastAPI · Next.js 14 · SQLAlchemy · JWT · PostgreSQL/SQLite · D3.js

**AI use disclosure:** This project was built with assistance from Claude (Anthropic) as a coding assistant for boilerplate generation and UI implementation. All architecture decisions, Cognee integration patterns, and core logic were designed by the developer.

---

### GitHub link to project
https://github.com/jeffychristaj/quorum

*(Push your local folder before submitting: `git init && git add . && git commit -m "feat: Quorum - production incident prevention with Cognee memory" && git remote add origin https://github.com/jeffychristaj/quorum.git && git push -u origin main`)*

---

### Deployed link to project
https://quorum-demo.vercel.app

*(Deploy frontend free in 2 minutes: `cd frontend && npx vercel --prod`)*
*(Backend: deploy to Railway.app — connect repo → set env vars → deploy)*

---

### YouTube video demo link
https://youtu.be/YOUR_VIDEO_ID

*(See Section 3 for the exact 3-minute script to record)*

---

### Describe how you have used Cognee in your project

Cognee is not a feature in Quorum — it IS Quorum's brain. Here's exactly how:

**1. Ingestion — building the knowledge graph**
Every deployment event and incident is ingested using Cognee's memory lifecycle:
```python
await cognee.add(deployment_text, dataset_name=f"quorum_{user_id[:8]}")
await cognee.cognify()  # builds the graph
```
This transforms raw deployment data into a queryable knowledge graph of relationships: services → deployments → incidents → root causes → safe states.

**2. GRAPH_COMPLETION — causal chain traversal (the core differentiator)**
When an anomaly fires, Quorum queries Cognee using graph traversal, not vector similarity:
```python
results = await cognee.search(
    SearchType.GRAPH_COMPLETION,
    query=f"What was the safe deployment before the {anomaly_type} incident?"
)
```
This traverses the causal chain: `anomaly → incident → root_cause → bad_deploy → safe_state` — returning the exact rollback commit with a confidence-scored recommendation. Plain RAG cannot do this because it finds similar text, not causal relationships.

**3. INSIGHTS — entity relationship extraction**
```python
insights = await cognee.search(SearchType.INSIGHTS, query=anomaly_description)
```
Used to extract (subject, relationship, object) triples from incident history — shown as graph edges in the D3.js knowledge graph visualization.

**4. SUMMARIES — high-level context for AI chat**
```python
summaries = await cognee.search(SearchType.SUMMARIES, query=user_message)
```
Powers the AI Assistant's system prompt with high-level operational context before querying the LLM.

**5. Persistent conversational memory**
After every AI chat exchange, the conversation is re-ingested into Cognee:
```python
await cognee.add(f"User: {user_msg}\nAssistant: {ai_response}", dataset_name=f"chat_{user_id[:8]}")
await cognee.cognify()
```
This means Quorum's AI assistant remembers every conversation, every incident, and every rollback — across sessions, across restarts. The memory graph grows richer with every incident your team resolves.

**6. Memory namespacing by user**
Each user's Cognee memory is namespaced by `user_id[:8]` so individuals have personal context while the org shares production memory — enabling both personal AI assistants and shared incident knowledge.

**Why Cognee and not plain RAG?**
The chain `anomaly → incident → root_cause → bad_deployment → safe_state` requires traversing *directed relationships* in a graph. A vector DB finds the most semantically similar incident. Cognee's GRAPH_COMPLETION finds the *causal path* from the current anomaly to the safe state. That is categorically impossible with embeddings alone.

---

### Link to the PR you have raised
https://github.com/topoteretes/cognee/pull/YOUR_PR_NUMBER

*(See Section 4 for the exact PR to raise, with complete code)*

---

### Blog link
https://dev.to/jeffychristaj/quorum-how-i-built-a-production-incident-ai-with-cognee-graph-memory

*(See Section 5 for the complete blog post draft — publish on dev.to or Hashnode)*

---

### How was your hackathon experience?

Building Quorum during "Where's My Context?" was the most intense and rewarding week of my developer journey. The challenge of making Cognee's graph-vector hybrid *genuinely necessary* — not just bolted on — forced me to think deeply about what separates graph traversal from plain RAG.

The "aha moment" came when I realized that production incident recall is literally a graph problem. The chain from anomaly to safe state is causal, not semantic — and that's exactly what GRAPH_COMPLETION solves. Every time I called `SearchType.GRAPH_COMPLETION` and got back a precise rollback commit instead of vague text matches, I knew I'd built something real.

The WeMakeDevs community and Cognee Discord were incredibly supportive. I went from idea to full production-grade app with auth, RBAC, multi-source ingestion, and a cinematic UI in under a week. Quorum is something I genuinely plan to ship as a real product.

---
