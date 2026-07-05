"""
Thin cognee functions for use as custom tools in Vellum's Agent Node.

These are plain async Python functions — no BaseNode subclassing required.
Register them in the Vellum UI under Agent Node → Custom Tools, or pass
them directly via the Workflows SDK.

    from cognee_integration_vellum.tools import cognee_remember, cognee_recall

The Agent Node decides *when* to call them; cognee decides *what* to store
and how to retrieve it.
"""

from __future__ import annotations

import logging
from typing import Optional

from .scoping import MemoryScope, resolve_dataset

logger = logging.getLogger(__name__)


async def cognee_remember(
    text: str,
    user_id: str = "",
    workflow_name: str = "",
    scope: str = "workflow",
) -> dict:
    """Store ``text`` in cognee's knowledge graph.

    Args:
        text:           The text to remember.
        user_id:        Per-user isolation (required when scope="user").
        workflow_name:  Overrides the VELLUM_WORKFLOW_NAME env var.
        scope:          "workflow" | "user" | "global"

    Returns:
        {"success": bool, "dataset": str, "error": str}
    """
    import cognee

    try:
        mem_scope = MemoryScope(scope)
    except ValueError:
        mem_scope = MemoryScope.WORKFLOW

    dataset = resolve_dataset(mem_scope, workflow_name=workflow_name, user_id=user_id)

    try:
        await cognee.add(text, dataset_name=dataset)
        await cognee.cognify()
        logger.info("cognee_remember: stored %d chars → %s", len(text), dataset)
        return {"success": True, "dataset": dataset, "error": ""}
    except Exception as exc:
        logger.error("cognee_remember failed: %s", exc)
        return {"success": False, "dataset": dataset, "error": str(exc)}


async def cognee_recall(
    query: str,
    user_id: str = "",
    workflow_name: str = "",
    scope: str = "workflow",
    top_k: int = 5,
) -> dict:
    """Retrieve information from cognee's knowledge graph.

    Args:
        query:          Natural-language question.
        user_id:        Per-user isolation.
        workflow_name:  Dataset routing override.
        scope:          "workflow" | "user" | "global"
        top_k:          Maximum citations to return.

    Returns:
        {
            "answer": str,           # graph-completion answer
            "citations": list[str],  # source node / document IDs
            "insights": list[dict],  # raw relationship triples
            "dataset": str,
        }
    """
    import cognee
    from cognee.api.v1.search import SearchType

    try:
        mem_scope = MemoryScope(scope)
    except ValueError:
        mem_scope = MemoryScope.WORKFLOW

    dataset = resolve_dataset(mem_scope, workflow_name=workflow_name, user_id=user_id)

    try:
        completion = await cognee.search(SearchType.GRAPH_COMPLETION, query_text=query)
        answer = completion[0].get("answer", "") if completion else ""

        insights = await cognee.search(SearchType.INSIGHTS, query_text=query)
        insights = insights[:top_k]
        citations = list(
            dict.fromkeys(
                r.get("object", r.get("subject", ""))
                for r in insights
                if r.get("object") or r.get("subject")
            )
        )

        logger.info("cognee_recall: query=%r → %d citations", query[:60], len(citations))
        return {"answer": answer, "citations": citations, "insights": insights, "dataset": dataset}

    except Exception as exc:
        logger.error("cognee_recall failed: %s", exc)
        return {"answer": "", "citations": [], "insights": [], "dataset": dataset}
