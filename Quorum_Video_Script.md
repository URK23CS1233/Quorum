# Quorum — 3-Minute Video Script
# WeMakeDevs × Cognee Hackathon Submission
# First Person · Avengers Narrative · All 4 Points Covered

---

## [0:00 – 0:30] ABOUT THE PROJECT

"Imagine it's 2 AM. Your team just pushed a deployment.
Five minutes later — error rate spikes to 18%.
CPU maxed. Latency at 3,800 milliseconds.
Production is down.

That's Thanos snapping his fingers.
And your engineering team? They're the Avengers —
scrambling through Slack, GitHub, Confluence,
trying to remember what changed, what to roll back to,
what the safe state was.

That's the problem I set out to solve.

I built **Quorum** — a production reliability platform
that gives your team a Time Machine for production.
And the Time Stone powering it? That's **Cognee**."

---

## [0:30 – 1:15] TECH STACK AND ARCHITECTURE

"Let me show you how it's built.

The backend is **FastAPI** in Python —
it handles deployment ingestion, live metrics over WebSocket,
an AI chat with Server-Sent Events streaming,
and role-based access for operators and analysts.

The frontend is **React with Vite** —
a cinematic dark-mode dashboard with a live metrics panel,
a knowledge graph visualizer, and a full chat interface.

But the brain — the actual intelligence — is **Cognee**.

Here's how Quorum uses Cognee at five points:

One — `cognee.add()`: every deployment, every incident,
every conversation is written into the knowledge graph.

Two — `cognee.cognify()`: Cognee processes that data
and builds relationships — which deployment caused which incident,
what the root cause was, which commit was the safe state.

Three — `cognee.search(GRAPH_COMPLETION)`:
when anomalies are detected, Quorum queries Cognee —
'have we seen this before? what's the safe state?'
And Cognee traverses the graph and answers.

Four and five — `INSIGHTS` and `SUMMARIES`:
surface connected facts and human-readable history
directly in the dashboard and AI chat.

The LLM for the chat is **Groq's LLaMA 3.3 70B** —
fast, smart, and wired directly into Cognee's memory
so every answer is grounded in your actual production history."

---

## [1:15 – 2:20] DEMO

"Let me walk you through a real scenario.

A deployment comes in — Marcus pushed a payment queue change.
Quorum ingests it automatically. Cognee learns it.
The dashboard shows stable metrics. All good.

Then — the batch processing overwhelms memory.
Error rate climbs. The metrics panel turns red.
Quorum's monitoring engine detects the anomaly
and fires a knowledge graph search against Cognee.

In seconds, Cognee responds:
'This matches a past incident — OOM from queue batch processing.
Safe rollback target: dep-001, commit a1b2c3d,
deployed by Sarah Chen, resolved in 18 minutes.'

That answer came from the knowledge graph —
not a keyword search, not a static runbook.
A graph traversal across every deployment and incident
Quorum has ever seen.

One click — rollback executed.
Metrics normalize. Audit log updated. Memory ingested.

Now I open the AI chat.
I type: 'What caused last night's incident?'

The assistant doesn't guess.
It recalls from Cognee's graph —
tells me the exact deployment, root cause, resolution time,
and who rolled it back.

This is persistent memory. This is the Time Stone.
Every incident makes the system smarter for the next one."

---

## [2:20 – 2:50] LEARNING AND GROWTH

"Building Quorum taught me things no tutorial ever could.

The hardest part wasn't the code —
it was understanding how a knowledge graph thinks.
Cognee doesn't just store data. It builds meaning.
And making Quorum ask the right questions of that graph
took real design thinking.

I also learned that production reliability is a human problem
as much as a technical one.
Teams lose knowledge when people leave.
Incidents repeat because nobody read the post-mortem.
The real feature of Quorum isn't the rollback button —
it's the memory that outlasts any individual engineer.

And personally — this hackathon pushed me to ship
a full-stack production-grade application
from scratch, in days, with a technology I had never used before.
That's growth I'll carry into every project from here."

---

## [2:50 – 3:00] CLOSE

"Quorum is a bet that your infrastructure deserves a memory.

That when Thanos snaps —
the Avengers already know how to go back.

I'm Jillu. This is Quorum.
Always knows your last agreed-upon safe state."

---

# DELIVERY NOTES

| Section | Time | Key visual on screen |
|---|---|---|
| About the project | 0:00–0:30 | Incident animation / error spike |
| Tech stack | 0:30–1:15 | Architecture diagram / code snippets |
| Demo | 1:15–2:20 | Live screen recording of dashboard + chat |
| Learning & growth | 2:20–2:50 | Talking head / personal |
| Close | 2:50–3:00 | Quorum logo + tagline |

**Tips:**
- Record the demo section as a screen recording first, then narrate over it
- Keep pace steady — this script reads at ~140 words/min, fits comfortably in 3 min
- You don't need to read word-for-word — use this as your outline and speak naturally
