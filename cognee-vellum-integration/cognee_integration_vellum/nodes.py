"""
Vellum Workflows SDK nodes backed by cognee's knowledge graph.

Three nodes are provided:

    CogneeRememberNode  — ingest text into cognee's graph (add + cognify).
    CogneeRecallNode    — query the graph; returns grounded answer + citations.
    CogneeMemoryDriftNode — detect when an LLM output diverges from stored facts.

All nodes read credentials from environment variables / Vellum workspace
secrets and never hardcode API keys.

Usage (code-first)::

    from cognee_integration_vellum.nodes import (
        CogneeRememberNode,
        CogneeRecallNode,
        CogneeMemoryDriftNode,
    )
    from cognee_integration_vellum.scoping import MemoryScope
    from vellum.workflows import BaseWorkflow

    class SupportWorkflow(BaseWorkflow):
        graph = CogneeRememberNode >> CogneeRecallNode

"""

from __future__ import annotations

import logging
import os
from typing import Optional

from vellum.workflows.nodes.bases import BaseNode
from vellum.workflows.types.core import MergeBehavior  # noqa: F401 (re-exported for graphs)

from .scoping import MemoryScope, resolve_dataset

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CogneeRememberNode
# ---------------------------------------------------------------------------


class CogneeRememberNode(BaseNode):
    """Ingest ``text`` into cognee's knowledge graph and run cognify.

    This node calls ``cognee.add(text, dataset_name=...)`` followed by
    ``cognee.cognify()`` so the information is immediately available for
    graph-completion queries.

    Inputs:
        text (str):
            The text / conversation turn to store.
        user_id (str):
            Per-user identifier. Required when ``scope=MemoryScope.USER``.
        workflow_name (str):
            Overrides the ``VELLUM_WORKFLOW_NAME`` env var for dataset routing.
        scope (MemoryScope):
            ``WORKFLOW`` (default) | ``USER`` | ``GLOBAL``.

    Outputs:
        success (bool):   True if ingestion succeeded.
        dataset (str):    The cognee dataset name that was written to.
        error (str):      Non-empty only when ``success=False``.
    """

    # ── inputs ────────────────────────────────────────────────────────────
    text: str
    user_id: str = ""
    workflow_name: str = ""
    scope: MemoryScope = MemoryScope.WORKFLOW

    # ── outputs ───────────────────────────────────────────────────────────
    class Outputs(BaseNode.Outputs):
        success: bool
        dataset: str
        error: str

    # ── init ──────────────────────────────────────────────────────────
    def __init__(self, *, text: str, user_id: str = "", workflow_name: str = "",
                 scope: "MemoryScope" = MemoryScope.WORKFLOW):
        self.text = text
        self.user_id = user_id
        self.workflow_name = workflow_name
        self.scope = scope

    # ── run ───────────────────────────────────────────────────────────────
    def run(self) -> Outputs:
        import asyncio
        import cognee

        dataset = resolve_dataset(
            self.scope,
            workflow_name=self.workflow_name,
            user_id=self.user_id,
        )

        async def _ingest() -> None:
            await cognee.add(self.text, dataset_name=dataset)
            await cognee.cognify()

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Inside an async context — schedule and wait
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _ingest())
                    future.result()
            else:
                loop.run_until_complete(_ingest())

            logger.info("CogneeRememberNode: ingested %d chars → dataset=%s", len(self.text), dataset)
            return self.Outputs(success=True, dataset=dataset, error="")

        except Exception as exc:
            logger.error("CogneeRememberNode failed: %s", exc)
            return self.Outputs(success=False, dataset=dataset, error=str(exc))


# ---------------------------------------------------------------------------
# CogneeRecallNode
# ---------------------------------------------------------------------------


class CogneeRecallNode(BaseNode):
    """Query cognee's knowledge graph and return a grounded answer with citations.

    Uses ``SearchType.GRAPH_COMPLETION`` to traverse causal chains and
    ``SearchType.INSIGHTS`` to extract entity relationships as structured
    citations.

    Inputs:
        query (str):          Natural-language question.
        user_id (str):        For scoped recall when ``scope=MemoryScope.USER``.
        workflow_name (str):  Dataset routing override.
        scope (MemoryScope):  ``WORKFLOW`` | ``USER`` | ``GLOBAL``.
        top_k (int):          Max results to surface (default 5).

    Outputs:
        answer (str):          Graph-completion answer.
        citations (list[str]): Source document / node IDs the answer derives from.
        insights (list[dict]): Raw relationship triples from INSIGHTS search.
        dataset (str):         The cognee dataset that was queried.
    """

    # ── inputs ────────────────────────────────────────────────────────────
    query: str
    user_id: str = ""
    workflow_name: str = ""
    scope: MemoryScope = MemoryScope.WORKFLOW
    top_k: int = 5

    # ── outputs ───────────────────────────────────────────────────────────
    class Outputs(BaseNode.Outputs):
        answer: str
        citations: list
        insights: list
        dataset: str

    # ── init ──────────────────────────────────────────────────────────
    def __init__(self, *, query: str, user_id: str = "", workflow_name: str = "",
                 scope: "MemoryScope" = MemoryScope.WORKFLOW, top_k: int = 5):
        self.query = query
        self.user_id = user_id
        self.workflow_name = workflow_name
        self.scope = scope
        self.top_k = top_k

    # ── run ───────────────────────────────────────────────────────────────
    def run(self) -> Outputs:
        import asyncio
        from cognee.api.v1.search import SearchType
        import cognee

        dataset = resolve_dataset(
            self.scope,
            workflow_name=self.workflow_name,
            user_id=self.user_id,
        )

        async def _search() -> tuple[str, list, list]:
            # Primary: graph-completion traversal
            completion_results = await cognee.search(
                SearchType.GRAPH_COMPLETION,
                query_text=self.query,
            )
            answer = (
                completion_results[0].get("answer", "")
                if completion_results
                else ""
            )

            # Secondary: relationship insights → structured citations
            insight_results = await cognee.search(
                SearchType.INSIGHTS,
                query_text=self.query,
            )
            insight_results = insight_results[: self.top_k]

            citations = list(
                dict.fromkeys(          # deduplicate, preserve order
                    r.get("object", r.get("subject", ""))
                    for r in insight_results
                    if r.get("object") or r.get("subject")
                )
            )
            return answer, citations, insight_results

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _search())
                    answer, citations, insights = future.result()
            else:
                answer, citations, insights = loop.run_until_complete(_search())

            logger.info(
                "CogneeRecallNode: query=%r → %d citations", self.query[:60], len(citations)
            )
            return self.Outputs(
                answer=answer,
                citations=citations,
                insights=insights,
                dataset=dataset,
            )

        except Exception as exc:
            logger.error("CogneeRecallNode failed: %s", exc)
            return self.Outputs(answer="", citations=[], insights=[], dataset=dataset)


# ---------------------------------------------------------------------------
# CogneeMemoryDriftNode  ← the novel feature
# ---------------------------------------------------------------------------


class CogneeMemoryDriftNode(BaseNode):
    """Detect when a workflow's LLM output diverges from cognee's stored knowledge.

    This node answers the question: *"Is the model hallucinating away from
    what we actually know?"*

    It works by:
    1. Recalling what cognee's graph says about ``query`` (ground truth).
    2. Computing a token-level Jaccard overlap between ``current_answer`` and
       the recalled ground truth. No extra ML model required.
    3. Returning a ``drift_score`` (0 = identical, 1 = completely diverged)
       along with the grounded answer and its citations.

    Inputs:
        query (str):
            The question the workflow posed to its LLM.
        current_answer (str):
            The LLM's output that you want to check.
        user_id (str):        Dataset scoping.
        workflow_name (str):  Dataset routing override.
        scope (MemoryScope):  ``WORKFLOW`` | ``USER`` | ``GLOBAL``.
        drift_threshold (float):
            Flag as drifting when score exceeds this (default 0.65).

    Outputs:
        drift_score (float):
            0.0 = grounded, 1.0 = fully diverged from stored knowledge.
        is_drifting (bool):
            True when ``drift_score > drift_threshold``.
        grounded_answer (str):
            What cognee's graph says the correct answer is.
        citations (list[str]):
            Source document / node IDs behind the grounded answer.
        current_answer (str):
            Echo of the input (convenience for downstream nodes).

    Why this matters
    ----------------
    Vellum already provides Evaluations for scoring LLM outputs against
    expected results — but those require golden datasets prepared upfront.
    ``CogneeMemoryDriftNode`` works *continuously* from the live knowledge
    graph, so every new execution is automatically checked against accumulated
    memory without any manual curation.
    """

    # ── inputs ────────────────────────────────────────────────────────────
    query: str
    current_answer: str
    user_id: str = ""
    workflow_name: str = ""
    scope: MemoryScope = MemoryScope.WORKFLOW
    drift_threshold: float = 0.65

    # ── outputs ───────────────────────────────────────────────────────────
    class Outputs(BaseNode.Outputs):
        drift_score: float
        is_drifting: bool
        grounded_answer: str
        citations: list
        current_answer: str
    # ── init ──────────────────────────────────────────────────────────
    def __init__(self, *, query: str, current_answer: str, user_id: str = "",
                 workflow_name: str = "", scope: "MemoryScope" = MemoryScope.WORKFLOW,
                 drift_threshold: float = 0.65):
        self.query = query
        self.current_answer = current_answer
        self.user_id = user_id
        self.workflow_name = workflow_name
        self.scope = scope
        self.drift_threshold = drift_threshold


    # ── helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _jaccard_distance(a: str, b: str) -> float:
        """Token-level Jaccard distance between two strings.

        Returns 0.0 when the strings are identical, 1.0 when they share no
        tokens. No external dependencies.
        """
        if not a and not b:
            return 0.0
        if not a or not b:
            return 1.0
        tokens_a = set(a.lower().split())
        tokens_b = set(b.lower().split())
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return 1.0 - len(intersection) / len(union)

    # ── run ───────────────────────────────────────────────────────────────
    def run(self) -> Outputs:
        import asyncio
        from cognee.api.v1.search import SearchType
        import cognee

        dataset = resolve_dataset(
            self.scope,
            workflow_name=self.workflow_name,
            user_id=self.user_id,
        )

        async def _recall() -> tuple[str, list]:
            completion = await cognee.search(
                SearchType.GRAPH_COMPLETION,
                query_text=self.query,
            )
            grounded = completion[0].get("answer", "") if completion else ""

            insights = await cognee.search(
                SearchType.INSIGHTS,
                query_text=self.query,
            )
            citations = list(
                dict.fromkeys(
                    r.get("object", r.get("subject", ""))
                    for r in insights[:5]
                    if r.get("object") or r.get("subject")
                )
            )
            return grounded, citations

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _recall())
                    grounded_answer, citations = future.result()
            else:
                grounded_answer, citations = loop.run_until_complete(_recall())

        except Exception as exc:
            logger.error("CogneeMemoryDriftNode recall failed: %s", exc)
            grounded_answer, citations = "", []

        drift_score = self._jaccard_distance(self.current_answer, grounded_answer)
        is_drifting = drift_score > self.drift_threshold

        if is_drifting:
            logger.warning(
                "CogneeMemoryDriftNode: DRIFT DETECTED score=%.2f query=%r",
                drift_score,
                self.query[:60],
            )

        return self.Outputs(
            drift_score=round(drift_score, 4),
            is_drifting=is_drifting,
            grounded_answer=grounded_answer,
            citations=citations,
            current_answer=self.current_answer,
        )
