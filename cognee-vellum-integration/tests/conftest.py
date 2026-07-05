"""
Pytest configuration: stub vellum and cognee before any test module imports.

This lets the full test suite run without the real packages installed, so CI
passes on every PR without requiring API keys or heavy dependencies.
"""

import sys
import types
import unittest.mock as mock


# ── vellum stub ────────────────────────────────────────────────────────────

class _BaseOutputs:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _BaseNode:
    class Outputs(_BaseOutputs):
        pass


_vellum = types.ModuleType("vellum")
_workflows = types.ModuleType("vellum.workflows")
_nodes_mod = types.ModuleType("vellum.workflows.nodes")
_bases = types.ModuleType("vellum.workflows.nodes.bases")
_bases.BaseNode = _BaseNode
_types_mod = types.ModuleType("vellum.workflows.types")
_core_mod = types.ModuleType("vellum.workflows.types.core")
_core_mod.MergeBehavior = None

sys.modules.update({
    "vellum": _vellum,
    "vellum.workflows": _workflows,
    "vellum.workflows.nodes": _nodes_mod,
    "vellum.workflows.nodes.bases": _bases,
    "vellum.workflows.types": _types_mod,
    "vellum.workflows.types.core": _core_mod,
})


# ── cognee stub ────────────────────────────────────────────────────────────

class _SearchType:
    GRAPH_COMPLETION = "GRAPH_COMPLETION"
    INSIGHTS = "INSIGHTS"
    SUMMARIES = "SUMMARIES"


_cognee = types.ModuleType("cognee")
_cognee.add = mock.AsyncMock()
_cognee.cognify = mock.AsyncMock()
_cognee.search = mock.AsyncMock(return_value=[])
_cognee.prune = types.SimpleNamespace(prune_data=mock.AsyncMock())

_cognee_api = types.ModuleType("cognee.api")
_cognee_api_v1 = types.ModuleType("cognee.api.v1")
_cognee_search = types.ModuleType("cognee.api.v1.search")
_cognee_search.SearchType = _SearchType

sys.modules.update({
    "cognee": _cognee,
    "cognee.api": _cognee_api,
    "cognee.api.v1": _cognee_api_v1,
    "cognee.api.v1.search": _cognee_search,
})
