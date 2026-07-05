"""
Quorum — shared pytest configuration & fixtures.

Loaded by pytest BEFORE any test module is imported. Responsibilities:

  1. Set safe test-only environment variables.
  2. Stub the *genuinely external* heavy dependencies that are not installed
     in the test environment (``cognee``, ``openai``). First-party modules
     (``quorum_engine``, ``metrics_simulator``, ``github_service``,
     ``cognee_service`` …) are imported for real so their logic is covered.
  3. Provide reusable fixtures: an isolated in-memory database, a configured
     FastAPI ``TestClient``, an authenticated-user factory, and autouse
     fixtures that reset module-level global state between tests.
"""

import os
import sys
import types
import unittest.mock as mock

import pytest

# ── env (must be set before app modules import config) ────────────
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_quorum.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-minimum!!")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake")
os.environ.setdefault("GITHUB_TOKEN", "")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")


# ── external dependency stubs ─────────────────────────────────────
def _stub(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m


class _SearchType:
    GRAPH_COMPLETION = "GRAPH_COMPLETION"
    INSIGHTS = "INSIGHTS"
    SUMMARIES = "SUMMARIES"


# cognee (graph-vector memory) — not installed in test env
_cognee = _stub(
    "cognee",
    add=mock.AsyncMock(),
    cognify=mock.AsyncMock(),
    search=mock.AsyncMock(return_value=[]),
    prune=types.SimpleNamespace(prune_data=mock.AsyncMock()),
)
_stub("cognee.api")
_stub("cognee.api.v1")
_stub("cognee.api.v1.search", SearchType=_SearchType)
_stub("cognee.infrastructure")
_stub("cognee.infrastructure.llm")
_stub(
    "cognee.infrastructure.llm.config",
    get_llm_config=mock.MagicMock(return_value=mock.MagicMock()),
)
_stub("cognee.infrastructure.databases")
_stub(
    "cognee.infrastructure.databases.graph",
    get_graph_engine=mock.AsyncMock(
        return_value=mock.AsyncMock(
            get_graph_data=mock.AsyncMock(return_value=([], []))
        )
    ),
)

# openai — not installed in test env
_openai = _stub("openai")
_openai.AsyncOpenAI = mock.MagicMock(return_value=mock.MagicMock())


# ── convenience access to the cognee stub for tests ───────────────
@pytest.fixture
def cognee_stub():
    """The stubbed ``cognee`` module (reset fresh for every test)."""
    return sys.modules["cognee"]


@pytest.fixture(autouse=True)
def _disable_rate_limiter():
    """
    Disable slowapi rate limiting during tests. The limiter keys on remote
    address; under TestClient every request shares one address, so the
    5/min register limit would otherwise leak 429s across unrelated tests.
    """
    import main
    import auth.router as auth_router

    main.limiter.enabled = False
    auth_router.limiter.enabled = False
    yield
    main.limiter.enabled = True
    auth_router.limiter.enabled = True


@pytest.fixture(autouse=True)
def _reset_external_stubs():
    """Reset the cognee/openai stubs to their default behaviour per test."""
    c = sys.modules["cognee"]
    c.add = mock.AsyncMock()
    c.cognify = mock.AsyncMock()
    c.search = mock.AsyncMock(return_value=[])
    c.prune = types.SimpleNamespace(prune_data=mock.AsyncMock())

    graph_mod = sys.modules["cognee.infrastructure.databases.graph"]
    graph_mod.get_graph_engine = mock.AsyncMock(
        return_value=mock.AsyncMock(
            get_graph_data=mock.AsyncMock(return_value=([], []))
        )
    )
    yield


# ── module-level global-state isolation ───────────────────────────
@pytest.fixture(autouse=True)
def _reset_module_state(tmp_path, monkeypatch):
    """
    Reset the in-process singletons that Quorum keeps at module scope so tests
    never leak state into one another. Also redirects the deployment registry
    file to a temp path so ``remember_deployment`` never writes into the repo.
    """
    import metrics_simulator
    import quorum_engine
    import cognee_service
    import chat.service as chat_service

    # metrics simulator
    metrics_simulator._state.update(
        {"mode": "healthy", "scenario": None, "incident_tick": 0}
    )
    metrics_simulator._subscribers.clear()

    # quorum engine
    quorum_engine._active_incident = None
    quorum_engine._incident_history.clear()
    quorum_engine._analysis_in_progress = False

    # cognee service registry (isolated per test)
    monkeypatch.setattr(
        cognee_service, "_REGISTRY_FILE", tmp_path / "quorum_deployments.json"
    )
    cognee_service._deployment_cache = None
    cognee_service._last_stable_deployment = None
    cognee_service._graph_enabled = True  # exercise the (stubbed) cognee path in tests

    # chat OpenAI client cache
    chat_service._oai = None

    yield


# ── database fixtures ─────────────────────────────────────────────
@pytest.fixture
def engine():
    """A fresh in-memory SQLite engine (shared across sessions via StaticPool)."""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    from database import Base
    import db_models  # noqa: F401  (register ORM models on Base)

    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture
def SessionLocal(engine):
    from sqlalchemy.orm import sessionmaker

    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture
def db_session(SessionLocal):
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── FastAPI TestClient (lifespan intentionally NOT run) ───────────
@pytest.fixture
def client(engine, SessionLocal):
    """
    A ``TestClient`` whose ``get_db`` dependency points at the in-memory test
    database. The app lifespan (background loops, cognee setup) is deliberately
    not started so tests stay deterministic.
    """
    from fastapi.testclient import TestClient
    from database import get_db
    from main import app

    def _override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    test_client = TestClient(app, raise_server_exceptions=False)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()


# ── authenticated-user factory ────────────────────────────────────
@pytest.fixture
def make_user(db_session):
    """
    Factory that creates an Organization + User of a given role directly in the
    test DB and returns ``(user, access_token)``. Use it to exercise
    role-gated endpoints without going through the registration flow.
    """
    from db_models import User, Organization, UserRole
    import auth.service as auth_svc

    created = {"n": 0}

    def _make(role=UserRole.OPERATOR, email=None, name="Fixture User",
              org=None, is_active=True, password="FixturePass123"):
        created["n"] += 1
        if email is None:
            email = f"user{created['n']}@quorum.test"
        if org is None:
            org = Organization(name=f"Org{created['n']}", slug=f"org-{created['n']}")
            db_session.add(org)
            db_session.flush()
        user = User(
            name=name, email=email,
            hashed_password=auth_svc.hash_password(password),
            role=role, org_id=org.id, is_active=is_active,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        token = auth_svc.create_access_token(user)
        return user, token

    return _make


@pytest.fixture
def auth_header(make_user):
    """Convenience: return an ``Authorization`` header for a user of ``role``."""
    def _header(role=None, **kw):
        from db_models import UserRole
        if role is None:
            role = UserRole.OPERATOR
        _user, token = make_user(role=role, **kw)
        return {"Authorization": f"Bearer {token}"}
    return _header
