# cognee-integration-vellum

Persistent, structured memory for [Vellum Workflows](https://docs.vellum.ai/developers/workflows-sdk/introduction) — backed by cognee's knowledge graph.

Vellum workflows are stateless between executions. This package makes them remember.

---

## What's included

| Component | What it does |
|---|---|
| `CogneeRememberNode` | Ingest text into cognee's graph (`add + cognify`). Appears as a block in the Vellum visual editor. |
| `CogneeRecallNode` | Query the graph with `GRAPH_COMPLETION` + `INSIGHTS`. Returns grounded answer **and** typed citations. |
| `CogneeMemoryDriftNode` | ⭐ **Novel** — detect when an LLM output diverges from stored facts. Returns a `drift_score` (0–1) and flags hallucinations automatically. |
| `cognee_remember` / `cognee_recall` | Thin async functions for use as **Agent Node custom tools** — no BaseNode required. |
| `MemoryScope` | Three isolation levels: `WORKFLOW` · `USER` · `GLOBAL`. |

---

## 5-minute quickstart

```bash
# 1. Install
pip install cognee-integration-vellum

# 2. Set env vars
cp .env.template .env
# fill in LLM_API_KEY and VELLUM_API_KEY

# 3. Run the demo
python examples/support_assistant.py
```

### Use in a Vellum workflow (code-first)

```python
from cognee_integration_vellum import (
    CogneeRememberNode,
    CogneeRecallNode,
    CogneeMemoryDriftNode,
    MemoryScope,
)
from vellum.workflows import BaseWorkflow

class SupportWorkflow(BaseWorkflow):
    graph = CogneeRememberNode >> CogneeRecallNode

    class Inputs(BaseWorkflow.Inputs):
        text: str          # conversation to ingest
        query: str         # question to answer

    class Outputs(BaseWorkflow.Outputs):
        answer   = CogneeRecallNode.Outputs.answer
        citations = CogneeRecallNode.Outputs.citations
```

### Push to the Vellum visual editor

```bash
vellum push
```

`CogneeRememberNode`, `CogneeRecallNode`, and `CogneeMemoryDriftNode` appear as
drag-and-drop blocks. Docstrings become the node descriptions shown to non-technical users.

---

## Memory scoping

By default, one Vellum workflow deployment maps to one cognee dataset.

```python
# Per-workflow (default) — dataset: "vellum_support-assistant"
CogneeRecallNode(query="...", scope=MemoryScope.WORKFLOW, workflow_name="support-assistant")

# Per-user — dataset: "vellum_support-assistant_u_alice"
CogneeRecallNode(query="...", scope=MemoryScope.USER, user_id="alice")

# Organisation-wide — dataset: "vellum_global"
CogneeRecallNode(query="...", scope=MemoryScope.GLOBAL)
```

---

## Drift detection — the novel feature

`CogneeMemoryDriftNode` answers: *"Is the model hallucinating away from what we actually know?"*

```python
drift_node = CogneeMemoryDriftNode(
    query="Why is my payment failing?",
    current_answer=llm_output,       # the answer your LLM just gave
    scope=MemoryScope.WORKFLOW,
    drift_threshold=0.65,
)
out = drift_node.run()

print(out.drift_score)       # 0.0 = identical to graph, 1.0 = fully diverged
print(out.is_drifting)       # True when score > threshold
print(out.grounded_answer)   # what cognee knows to be true
print(out.citations)         # source documents behind the ground truth
```

**Why this beats Vellum Evaluations for drift:**
Vellum Evaluations need golden datasets prepared upfront. `CogneeMemoryDriftNode` checks against the *live knowledge graph* on every execution — no manual curation. Each new conversation that gets ingested improves the drift detector automatically.

### Drift in a workflow graph

```python
class SafeAnswerWorkflow(BaseWorkflow):
    # LLM generates answer → drift check → conditional output
    graph = MyLLMNode >> CogneeMemoryDriftNode

    class Outputs(BaseWorkflow.Outputs):
        answer        = CogneeMemoryDriftNode.Outputs.current_answer
        drift_score   = CogneeMemoryDriftNode.Outputs.drift_score
        is_drifting   = CogneeMemoryDriftNode.Outputs.is_drifting
        grounded      = CogneeMemoryDriftNode.Outputs.grounded_answer
```

---

## Agent Node tools (zero-code alternative)

If you prefer Vellum's visual Agent Node over code-first nodes:

```python
from cognee_integration_vellum.tools import cognee_remember, cognee_recall

# Register as custom tools in the Agent Node UI
# The agent decides when to call them.
```

> **Tip:** The Agent Node also supports MCP tools — `cognee-mcp` works today
> with zero code via the Agent Node's MCP server field. Use that when you want
> the agent to freely decide what to remember. Use `CogneeRecallNode` /
> `CogneeRememberNode` when you want deterministic, schema-enforced memory steps
> inside a defined workflow graph.

---

## Credentials

All API keys come from environment variables or Vellum workspace secrets — never hardcoded.

| Variable | Used by |
|---|---|
| `LLM_API_KEY` | cognee (for `cognify` graph enrichment) |
| `VELLUM_API_KEY` | `vellum push` (visual editor sync) |
| `VELLUM_WORKFLOW_NAME` | Default dataset name for `MemoryScope.WORKFLOW` |

---

## Development

```bash
uv sync --dev
uv run pytest tests/ -v
uv run ruff check .
```

---

## License

Apache 2.0 — see [LICENSE](../../LICENSE).
