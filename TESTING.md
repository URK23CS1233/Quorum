# Quorum — Testing Guide

Quorum has an automated test suite covering both the FastAPI backend and the
Next.js frontend — **252 tests** in total.

| Layer | Framework | Tests | Location |
|-------|-----------|-------|----------|
| Backend | `pytest` + `pytest-asyncio` | 220 | `backend/tests/` |
| Frontend | `vitest` + `@testing-library/react` (jsdom) | 32 | `frontend/src/**/*.test.ts(x)` |

Heavy external services (Cognee, the OpenAI/Groq LLM, the GitHub API) are
stubbed, so the suite runs offline with no API keys and no database server.

---

## Backend

```bash
cd backend
pip install -r requirements.txt      # installs pytest + pytest-asyncio
pytest                               # run everything
pytest tests/unit                    # unit tests only
pytest tests/integration             # integration tests only
pytest -k rollback -v                # filter by name
```

### Layout

```
backend/
  conftest.py            # env + external-dependency stubs + shared fixtures
  pytest.ini             # asyncio mode, test discovery
  tests/
    test_smoke.py        # fixture / app-wiring sanity checks
    unit/                # pure logic — models, engine, services, RBAC
      test_models.py
      test_metrics_simulator.py
      test_quorum_engine.py
      test_cognee_service.py
      test_github_service.py
      test_auth_service.py
      test_sources_service.py
      test_chat_service.py
      test_dependencies.py
    integration/         # HTTP + WebSocket through a FastAPI TestClient
      test_auth_api.py
      test_monitor_api.py
      test_memory_api.py
      test_simulate_rollback_graph_api.py
      test_users_api.py
      test_sources_api.py
      test_chat_api.py
      test_security_and_ws.py
```

### How the fixtures work (`conftest.py`)

- **External stubs** — `cognee` and `openai` are replaced with `AsyncMock`s so
  no ML stack or API key is required. First-party modules
  (`quorum_engine`, `metrics_simulator`, `github_service`, `cognee_service`,
  the routers) are imported for real and exercised directly.
- **`client`** — a `TestClient` whose `get_db` dependency points at a fresh
  in-memory SQLite database (`StaticPool`). The app lifespan (background
  loops, Cognee setup) is intentionally *not* started, keeping tests
  deterministic.
- **`make_user` / `auth_header`** — factories that create an
  Organization + User of a given role and return a valid JWT, so role-gated
  endpoints can be tested across the `SUPER_ADMIN → VIEWER` hierarchy.
- **Autouse isolation** — module-level singletons (the metrics simulator
  state, the active incident, the deployment registry) are reset between
  tests, and rate limiting is disabled so `slowapi` doesn't leak `429`s.

---

## Frontend

```bash
cd frontend
npm install                          # installs vitest + testing-library
npm test                             # run once
npm run test:watch                   # watch mode
npm run test:coverage                # coverage report (src/lib)
```

### What's covered

- `src/lib/auth.test.ts` — token storage, the role hierarchy
  (`hasRole`/`canOperate`/`canAdmin`/…), and badge styling.
- `src/lib/api.test.ts` — bearer-token injection, the **401 → refresh →
  retry** flow, SSE stream parsing (`streamChat`), and the metrics
  `WebSocket` factory. `fetch` and `WebSocket` are mocked.
- `src/components/IncidentPanel.test.tsx` — component rendering of the
  healthy vs. incident states and the rollback interaction.

---

## Notes

While writing these tests, three latent bugs were found and fixed:

1. **`main.py`** — a corrupted trailing line (`rics_simulator…`) that broke
   the entire app import.
2. **`github_service.py`** — an `UnboundLocalError` (`files` referenced before
   assignment) whenever a per-commit GitHub request failed.
3. **`auth/service.py`** — token refresh compared a naive datetime (returned
   by SQLite, the default store) against a tz-aware one, raising `TypeError`.

`bcrypt` is pinned to `4.0.1` in `requirements.txt` because `passlib` 1.7.4 is
incompatible with `bcrypt >= 4.1`.
