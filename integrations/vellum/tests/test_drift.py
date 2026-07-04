"""Tests for CogneeMemoryDriftNode — the novel feature.

Stubs for vellum and cognee are loaded by conftest.py before this module
is imported, so no API keys or installed packages are needed.
"""

import sys
import unittest.mock as mock
import pytest

from cognee_integration_vellum.nodes import CogneeMemoryDriftNode

# Grab the cognee stub (already in sys.modules from conftest.py)
_cognee_stub = sys.modules["cognee"]


# ── Jaccard distance unit tests ────────────────────────────────────────────

class TestJaccardDistance:
    def test_identical_strings_score_zero(self):
        score = CogneeMemoryDriftNode._jaccard_distance("hello world", "hello world")
        assert score == 0.0

    def test_disjoint_strings_score_one(self):
        score = CogneeMemoryDriftNode._jaccard_distance("apple banana", "carrot dragon")
        assert score == 1.0

    def test_partial_overlap(self):
        score = CogneeMemoryDriftNode._jaccard_distance("the cat sat", "the dog sat")
        # shared: {the, sat} = 2, union: {the, cat, sat, dog} = 4 → jaccard=0.5 → dist=0.5
        assert score == pytest.approx(0.5, abs=0.01)

    def test_empty_strings_score_zero(self):
        assert CogneeMemoryDriftNode._jaccard_distance("", "") == 0.0

    def test_one_empty_string_score_one(self):
        assert CogneeMemoryDriftNode._jaccard_distance("hello", "") == 1.0

    def test_case_insensitive(self):
        score = CogneeMemoryDriftNode._jaccard_distance("Hello World", "hello world")
        assert score == 0.0


# ── Integration tests (cognee stubbed) ────────────────────────────────────

class TestCogneeMemoryDriftNode:
    def _run_node(self, query, current_answer, grounded_answer, citations=None):
        """Helper: configure stub and run the node synchronously."""
        citations = citations or []
        search_results_by_type = {
            "GRAPH_COMPLETION": [{"answer": grounded_answer}],
            "INSIGHTS": [{"subject": c, "relationship": "related_to", "object": c}
                         for c in citations],
        }

        async def _search(search_type, query_text=""):
            return search_results_by_type.get(str(search_type), [])

        _cognee_stub.search = mock.AsyncMock(side_effect=_search)

        node = CogneeMemoryDriftNode(
            query=query,
            current_answer=current_answer,
            workflow_name="test-workflow",
            drift_threshold=0.65,
        )
        return node.run()

    def test_grounded_answer_no_drift(self):
        """When LLM output matches stored knowledge, drift_score is low."""
        out = self._run_node(
            query="What is our refund policy?",
            current_answer="Refunds are processed within 30 days of purchase.",
            grounded_answer="Refunds are processed within 30 days of purchase.",
        )
        assert out.drift_score == pytest.approx(0.0, abs=0.01)
        assert out.is_drifting is False

    def test_completely_diverged_answer_flags_drift(self):
        """When LLM output shares no tokens with stored knowledge, drift is 1.0."""
        out = self._run_node(
            query="What is our refund policy?",
            current_answer="Unicorns frolic near purple mountains.",
            grounded_answer="Refunds are processed within thirty days.",
        )
        assert out.drift_score > 0.65
        assert out.is_drifting is True

    def test_citations_returned(self):
        out = self._run_node(
            query="Revenue Q4?",
            current_answer="Revenue was 2.5M.",
            grounded_answer="Q4 revenue reached 2.5 million dollars.",
            citations=["doc-revenue-q4", "report-2024"],
        )
        assert "doc-revenue-q4" in out.citations

    def test_empty_graph_gives_max_drift(self):
        """If cognee has no memory yet, distance vs empty string is 1.0."""
        out = self._run_node(
            query="anything",
            current_answer="some answer",
            grounded_answer="",  # nothing in graph
        )
        assert out.drift_score == 1.0
        assert out.is_drifting is True

    def test_current_answer_echoed(self):
        out = self._run_node("q", "my answer", "my answer")
        assert out.current_answer == "my answer"

    def test_custom_threshold(self):
        # drift_threshold > 1.0 means nothing can ever be flagged (max Jaccard = 1.0)
        node = CogneeMemoryDriftNode(
            query="q",
            current_answer="apple",
            workflow_name="wf",
            drift_threshold=1.01,
        )
        _cognee_stub.search = mock.AsyncMock(return_value=[{"answer": "orange"}])
        out = node.run()
        assert out.is_drifting is False
        assert out.drift_score <= 1.0
