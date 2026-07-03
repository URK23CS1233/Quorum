"""
pytest conftest — stubs out heavy external dependencies (cognee, openai, etc.)
so auth tests run without installing the full ML stack.
Loaded by pytest BEFORE any test module is imported.
"""

import sys
import types
import unittest.mock as mock
import os

# ── env ───────────────────────────────────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_quorum.db")
os.environ.setdefault("JWT_SECRET", "test-secret-key-32-chars-minimum!!")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")


def _stub(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m


# ── cognee ────────────────────────────────────────────────────
class _SearchType:
    GRAPH_COMPLETION = "GRAPH_COMPLETION"
    INSIGHTS         = "INSIGHTS"
    SUMMARIES        = "SUMMARIES"

_stub("cognee",
    add     = mock.AsyncMock(),
    cognify = mock.AsyncMock(),
    search  = mock.AsyncMock(return_value=[]),
    prune   = types.SimpleNamespace(prune_data=mock.AsyncMock()),
)
_stub("cognee.api")
_stub("cognee.api.v1")
_stub("cognee.api.v1.search", SearchType=_SearchType)
_stub("cognee.infrastructure")
_stub("cognee.infrastructure.llm")
_stub("cognee.infrastructure.llm.config",
    get_llm_config=mock.MagicMock(return_value=mock.MagicMock()))
_stub("cognee.infrastructure.databases")
_stub("cognee.infrastructure.databases.graph",
    get_graph_engine=mock.AsyncMock(
        return_value=mock.AsyncMock(
            get_graph_data=mock.AsyncMock(return_value=([], [])))))

# ── openai ────────────────────────────────────────────────────
_openai = _stub("openai")
_openai.AsyncOpenAI = mock.MagicMock(return_value=mock.MagicMock())

# ── aiofiles ──────────────────────────────────────────────────
_stub("aiofiles")

# ── github_service ────────────────────────────────────────────
_stub("github_service",
    fetch_recent_commits=mock.AsyncMock(return_value=[]))

# ── metrics_simulator ─────────────────────────────────────────
_stub("metrics_simulator",
    broadcast_loop   = mock.AsyncMock(),
    current_mode     = mock.MagicMock(return_value="normal"),
    trigger_incident = mock.MagicMock(),
    resolve_incident = mock.MagicMock(),
    subscribe        = mock.MagicMock(return_value=mock.AsyncMock()),
    unsubscribe      = mock.MagicMock(),
)

# ── quorum_engine ─────────────────────────────────────────────
_stub("quorum_engine",
    monitor_loop          = mock.AsyncMock(),
    get_active_incident   = mock.MagicMock(return_value=None),
    clear_active_incident = mock.MagicMock(),
    execute_rollback      = mock.AsyncMock(return_value={"status": "ok"}),
)
