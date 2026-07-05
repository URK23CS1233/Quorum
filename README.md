# Quorum
### *"Always knows your last agreed-upon safe state."*

> Built for the **Cognee "The Hangover Part AI" Hackathon** · Open Source Track

Quorum is an AI-powered production incident prevention system. It remembers every deployment, detects anomalies in real-time, and surfaces the exact safe rollback commit before a human can make a mistake.

**AI removes error from the DECISION. You keep control of the ACTION.**

---

## The Problem

Production incidents kill companies. The P1 playbook is always the same:
1. Something breaks at 2am
2. On-call engineer scrambles through deployment history
3. They pick the wrong rollback target under pressure
4. Outage extends from 12 minutes to 2 hours

The error isn't technical. It's human. And it's preventable.

---

## Why Quorum Needs Cognee (Not Just RAG)

When production breaks, you need to traverse a causal chain:

```
current anomaly → similar past incident → root cause → bad deployment → safe state before it
```

Plain vector search finds "similar text." Cognee's graph-vector hybrid traverses **causal relationships**. That's not a subtle distinction — it's the entire reason rollback recommendations are accurate instead of guessed.

| | Plain RAG | Quorum + Cognee |
|---|---|---|
| Find similar incident | ✓ | ✓ |
| Trace root cause chain | ✗ | ✓ |
| Identify safe deployment | ✗ | ✓ |
| Learn from each rollback | ✗ | ✓ |

---

## Architecture

```
Production Metrics (WebSocket, 2s)
        │
        ▼
┌─────────────────┐
│  Quorum Engine  │  ← anomaly detection
│  (monitor loop) │
└────────┬────────┘
         │ anomaly detected
         ▼
┌─────────────────┐
│ Cognee Memory   │  cognee.search(GRAPH_COMPLETION)
│ Graph + Vector  │  cognee.search(INSIGHTS)
└────────┬────────┘  cognee.search(SUMMARIES)
         │ safe state identified
         ▼
┌─────────────────┐
│ Incident Panel  │  → human sees: safe commit + confidence + graph insights
│ (React UI)      │
└────────┬────────┘
         │ human clicks Confirm
         ▼
┌─────────────────┐
│ Execute Rollback│  → Quorum learns from this (remember_incident)
│ + Learn         │
└─────────────────┘
```

---

## Quick Start

```bash
# 1. Backend
cd backend
cp .env.example .env   # add your OPENAI_API_KEY
pip install -r requirements.txt
uvicorn main:app --reload

# 2. Seed memory (new terminal, backend must be running)
cd demo_data
python seed_incidents.py

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev

# 4. Open http://localhost:3000
```

---

## Demo Flow

1. **Open** http://localhost:3000 — you'll see live metrics streaming
2. **Simulate → Error Storm** — error rate spikes to 18%
3. **Watch** Quorum detect the anomaly in ~6 seconds
4. **Read** the Incident Panel — Cognee has recalled the matching past incident
5. **See** the safe state: exact deployment ID, commit SHA, commit message
6. **Click** "Confirm Rollback" — metrics recover, Quorum learns
7. **Switch** to Knowledge Graph tab — see the Cognee memory visualised

---

## API Reference

```bash
# Ingest deployment
POST /api/memory/deployment
{ "deployment": { "commit_sha": "...", "commit_message": "...", ... } }

# Ingest resolved incident
POST /api/memory/incident
{ "incident": { "root_cause": "...", "rolled_back_to_deployment": "dep-001", ... } }

# Ingest real GitHub history
POST /api/memory/github/{owner}/{repo}

# Trigger simulation
POST /api/simulate/incident
{ "scenario": "error_storm" }   # or: cpu_spike, latency_blowup, memory_leak

# Human-confirmed rollback
POST /api/rollback
{ "target_deployment_id": "dep-001" }

# Live metrics WebSocket
WS /ws/metrics  →  { type: "metrics", data: {...} }
                    { type: "incident", data: QuorumAnalysis }
```

---

## Testing

```bash
# Backend — 220 pytest tests (offline; external services stubbed)
cd backend && pip install -r requirements.txt && pytest

# Frontend — 32 Vitest tests
cd frontend && npm install && npm test
```

See [TESTING.md](TESTING.md) for the full layout and fixture design.

---

## Stack

- **Cognee** — graph-vector hybrid memory (the core)
- **FastAPI + WebSocket** — async Python backend
- **Next.js 14 + TypeScript** — React frontend
- **D3.js** — knowledge graph visualisation
- **LanceDB + NetworkX** — default Cognee stores (zero config)
- **Neo4j + Qdrant + Postgres** — production stores (docker-compose)

---

## Production Stores

The defaults (LanceDB + NetworkX) work locally with zero config. For production scale:

```bash
docker compose up -d

# then add to .env:
GRAPH_DATABASE_PROVIDER=neo4j
GRAPH_DATABASE_URL=bolt://localhost:7687
VECTOR_DB_PROVIDER=qdrant
QDRANT_PATH=http://localhost:6333
```

---

*Quorum — Always knows your last agreed-upon safe state.*
