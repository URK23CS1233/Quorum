"""
Quorum — Production FastAPI Application
"Always knows your last agreed-upon safe state."
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

# ── Rate limiter (shared across routers) ──────────────────────
limiter = Limiter(key_func=get_remote_address)

# Core services
import cognee_service
import github_service
import metrics_simulator
import quorum_engine

# DB
from database import get_db, create_tables

# Models
from models import (
    IngestDeploymentRequest, IngestIncidentRequest,
    RollbackRequest, SimulateIncidentRequest,
)

# Routers
from auth.router    import router as auth_router
from users.router   import router as users_router
from sources.router import router as sources_router
from chat.router    import router as chat_router

# Dependencies
from dependencies import require_analyst, require_operator, get_current_user
from db_models import User

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("quorum")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    await cognee_service.setup()
    asyncio.create_task(metrics_simulator.broadcast_loop(2.0))
    asyncio.create_task(quorum_engine.monitor_loop())
    logger.info("🔒 Quorum is online.")
    yield
    logger.info("Quorum shutting down.")


app = FastAPI(title="Quorum API", version="2.0.0", lifespan=lifespan)

# ── Rate limiter wiring ────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from config import get_settings
settings = get_settings()
cors_origins = settings.CORS_ORIGINS.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Security headers ───────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]  = "nosniff"
        response.headers["X-Frame-Options"]         = "DENY"
        response.headers["X-XSS-Protection"]        = "1; mode=block"
        response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]      = "camera=(), microphone=(), geolocation=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(sources_router)
app.include_router(chat_router)


# ── Health ────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "status": "ok", "service": "Quorum v2",
        "tagline": "Always knows your last agreed-upon safe state.",
    }

@app.get("/health")
async def health():
    return {"status": "ok", "mode": metrics_simulator.current_mode()}


# ── Memory endpoints (protected) ──────────────────────────────
@app.post("/api/memory/deployment")
async def ingest_deployment(
    body: IngestDeploymentRequest,
    current_user: User = Depends(require_operator),
):
    await cognee_service.remember_deployment(body.deployment)
    return {"status": "ok", "deployment_id": body.deployment.id}


@app.post("/api/memory/incident")
async def ingest_incident(
    body: IngestIncidentRequest,
    current_user: User = Depends(require_operator),
):
    await cognee_service.remember_incident(body.incident)
    return {"status": "ok", "incident_id": body.incident.id}


@app.post("/api/memory/github/{owner}/{repo}")
async def ingest_github(
    owner: str, repo: str, limit: int = 10,
    current_user: User = Depends(require_operator),
):
    deployments = await github_service.fetch_recent_commits(owner, repo, limit)
    if not deployments:
        raise HTTPException(404, f"No commits found for {owner}/{repo}")
    for dep in deployments:
        await cognee_service.remember_deployment(dep)
    return {"status": "ok", "ingested": len(deployments)}


@app.post("/api/memory/improve")
async def improve_memory(current_user: User = Depends(require_operator)):
    return await cognee_service.improve()


@app.delete("/api/memory")
async def forget_memory(
    dataset: str = "quorum_incidents",
    current_user: User = Depends(require_operator),
):
    return await cognee_service.forget(dataset)


# ── Graph ─────────────────────────────────────────────────────
@app.get("/api/graph")
async def get_graph(current_user: User = Depends(require_analyst)):
    return await cognee_service.get_graph_data()


# ── Monitor ───────────────────────────────────────────────────
@app.get("/api/monitor/status")
async def monitor_status(current_user: User = Depends(require_analyst)):
    return {
        "mode": metrics_simulator.current_mode(),
        "has_incident": quorum_engine.get_active_incident() is not None,
        "last_stable_deployment": (
            cognee_service.get_last_stable_deployment().dict()
            if cognee_service.get_last_stable_deployment() else None
        ),
        "deployment_count": len(cognee_service.get_all_deployments()),
    }


@app.get("/api/monitor/incident")
async def get_incident(current_user: User = Depends(require_analyst)):
    inc = quorum_engine.get_active_incident()
    if not inc:
        return {"active": False}
    return {"active": True, "analysis": inc.dict()}


@app.get("/api/monitor/deployments")
async def list_deployments(current_user: User = Depends(require_analyst)):
    return {"deployments": [d.dict() for d in cognee_service.get_all_deployments()]}


# ── Simulation ────────────────────────────────────────────────
@app.post("/api/simulate/incident")
async def simulate_incident(
    body: SimulateIncidentRequest,
    current_user: User = Depends(require_operator),
):
    metrics_simulator.trigger_incident(body.scenario)
    return {"status": "ok", "scenario": body.scenario}


@app.post("/api/simulate/resolve")
async def simulate_resolve(current_user: User = Depends(require_operator)):
    metrics_simulator.resolve_incident()
    quorum_engine.clear_active_incident()
    return {"status": "ok", "message": "Incident resolved."}


# ── Rollback ──────────────────────────────────────────────────
@app.post("/api/rollback")
async def rollback(
    body: RollbackRequest,
        current_user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    from db_models import AuditLog
    result = await quorum_engine.execute_rollback(body.target_deployment_id, body.reason)
    if result["status"] == "error":
        raise HTTPException(404, result["message"])
    db.add(AuditLog(
        user_id=current_user.id, action="rollback.execute",
        resource=body.target_deployment_id, details=body.reason,
    ))
    db.commit()
    return result


# ── WebSocket: live metrics (auth via query param token) ──────
@app.websocket("/ws/metrics")
async def ws_metrics(ws: WebSocket, token: str = ""):
    if token:
        try:
            from dependencies import _decode_token
            _decode_token(token)
        except Exception:
            await ws.close(code=4001)
            return

    await ws.accept()
    queue = metrics_simulator.subscribe()
    try:
        while True:
            payload  = await queue.get()
            incident = quorum_engine.get_active_incident()
            await ws.send_json({"type": "metrics", "data": payload})
            if incident:
                await ws.send_json({"type": "incident", "data": incident.dict()})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WS error: {e}")
    finally:
        metrics_simulator.unsubscribe(queue)
rics_simulator.unsubscribe(queue)
