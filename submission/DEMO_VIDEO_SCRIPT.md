# 3-Minute Demo Video Script
## Record with Loom, OBS, or QuickTime

---

## SETUP BEFORE RECORDING
- Start backend: `cd backend && uvicorn main:app --reload`
- Start frontend: `cd frontend && npm run dev`
- Open http://localhost:3000 in Chrome (full screen, zoom 90%)
- Have DevTools closed
- Use a clean browser profile (no extensions visible)
- Record at 1920×1080

---

## [0:00–0:20] Hook — The Problem

**Say (while showing landing page animating in):**
> "Every engineering team has experienced this: it's 2am, production is down, error rate is at 18%, and you're frantically asking — what changed? Which deploy broke this? What do I roll back to?"
>
> "The answer is in your incident history — buried in Slack, Confluence, and people's memory. Quorum changes that."

*Camera: screen recording of landing page — gradient text, floating orbs, stats counting up*

---

## [0:20–0:45] What is Quorum

**Say:**
> "Quorum is a production incident prevention platform powered by Cognee's graph-vector memory. It builds a living knowledge graph of every deployment, incident, and rollback — so when things break, the AI already knows the fix."

*Click "Get Started" — registration form animates in*

**Say:**
> "Let me show you. I'll register as SUPER_ADMIN of my org."

*Fill form quickly, submit — dashboard loads with page-enter animation*

---

## [0:45–1:30] Live Incident Demo (THE CORE)

**Say:**
> "This is the live monitor. All systems are currently healthy."

*Show metrics dashboard — green gauges*

**Say:**
> "Let me simulate a real production scenario — an error storm."

*Click Simulate → Error Storm — metrics spike dramatically*

**Say:**
> "Watch what happens. CPU is at 96%, error rate at 18% — and Cognee has already recalled our incident history."

*Incident panel slides in from right with red pulsing border*

**Say:**
> "Quorum used Cognee's GRAPH_COMPLETION to traverse the causal chain — from this anomaly, back to the last time we saw an error storm, to the deployment that caused it, to the safe state before that deploy."
>
> "High confidence. Safe rollback: commit `7d2e891` — 'refactor: improve checkout flow'. This is not a guess. This is graph traversal."

*Point at the safe state panel and confidence badge*

**Say:**
> "One click. Rollback confirmed."

*Click "Confirm Rollback" — metrics recover, flash message appears*

---

## [1:30–2:00] AI Memory Chat

*Navigate to AI Assistant with sidebar animation*

**Say:**
> "Now here's the part that makes Quorum more than a dashboard. Every incident and rollback is ingested into Cognee memory. So I can ask natural questions."

*Type: "What caused our last error storm?"*

*Typing indicator appears, then response streams in*

**Say:**
> "Cognee's graph memory — not an LLM hallucination — gives me: the exact deployment, the root cause, the author, the commit. Context that persists across sessions because it's stored in the graph."

---

## [2:00–2:30] Architecture (30 seconds)

*Open a split: code editor showing cognee_service.py on one side, knowledge graph on other*

**Say:**
> "Under the hood: every deployment and incident is ingested with cognee.add() and cognify(). Three search types power different features."
>
> "GRAPH_COMPLETION for rollback recall — it literally traverses the causal path in the graph. INSIGHTS for entity relationships — you can see them here in the D3 knowledge graph. SUMMARIES for the AI assistant's context window."
>
> "Plain RAG finds similar text. Cognee finds causal chains. That's the entire difference between 'something went wrong' and 'roll back to this exact commit.'"

*Show D3 graph with nodes animating*

---

## [2:30–3:00] Closing Pitch

**Say:**
> "Quorum is production-ready: JWT auth with 5 RBAC roles, multi-source ingestion from GitHub, PagerDuty, and Datadog, and a full team management UI."
>
> "The average MTTR for a production incident is 4.5 hours. With Quorum and Cognee, it's the time it takes to click one button."
>
> "Quorum. Always knows your last agreed-upon safe state."

*End on landing page with the tagline visible*

---

## RECORDING TIPS
- Speak slowly and clearly — you'll sound faster on playback
- Use `Cmd+K` / `Ctrl+K` to clear terminal between takes  
- If you stumble, pause 3 seconds and redo that sentence — easy to cut in editing
- Add captions via YouTube auto-caption after uploading
- Title: "Quorum — Production Incident Prevention with Cognee Graph Memory"
- Description: "Built for the WeMakeDevs × Cognee 'Where's My Context?' Hackathon 2026"

