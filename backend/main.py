"""
Quorum -- Production FastAPI Application
"Always knows your last agreed-upon safe state."
"""

import asyncio
import logging
import datetime
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

limiter = Limiter(key_func=get_remote_address)

import cognee_service
import github_service
import metrics_simulator
import quorum_engine

from database import get_db, create_tables
from models import (
    IngestDeploymentRequest, IngestIncidentRequest,
    RollbackRequest, SimulateIncidentRequest,
)
from auth.router    import router as auth_router
from users.router   import router as users_router
from sources.router import router as sources_router
from chat.router    import router as chat_router
from dependencies import require_analyst, require_operator, get_current_user
from db_models import User

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("quorum")


async def _auto_seed_demo_data():
    """Seed demo deployments and incidents if memory is empty (first run only)."""
    if cognee_service.get_all_deployments():
        return
    logger.info("No deployments in memory -- auto-seeding demo data...")
    from models import Deployment, Incident

    now = str(datetime.datetime.utcnow())

    DEMO_DEPLOYMENTS = [
        Deployment(id="dep-001",
            commit_sha="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            commit_message="Initial production rollout -- payment service v2.0",
            author="Sarah Chen", branch="main", repo="acme/platform",
            services_affected=["payment-service", "api-gateway"],
            cpu_at_deploy=24.0, error_rate_at_deploy=0.07, latency_at_deploy=88.0,
            status="STABLE", timestamp=now),
        Deployment(id="dep-002",
            commit_sha="b2c3d4e5f6a7b2c3d4e5f6a7b2c3d4e5f6a7b2c3",
            commit_message="feat: switch payment queue to batch processing (500ms flush)",
            author="Marcus Kim", branch="feature/payment-batching", repo="acme/platform",
            services_affected=["payment-service", "queue-worker"],
            cpu_at_deploy=27.5, error_rate_at_deploy=0.09, latency_at_deploy=92.0,
            status="INCIDENT", timestamp=now),
        Deployment(id="dep-003",
            commit_sha="c3d4e5f6a7b8c3d4e5f6a7b8c3d4e5f6a7b8c3d4",
            commit_message="revert: undo payment queue batch processing -- OOM in prod",
            author="Sarah Chen", branch="main", repo="acme/platform",
            services_affected=["payment-service", "queue-worker"],
            cpu_at_deploy=22.0, error_rate_at_deploy=0.07, latency_at_deploy=89.0,
            status="STABLE", timestamp=now),
        Deployment(id="dep-004",
            commit_sha="d4e5f6a7b8c9d4e5f6a7b8c9d4e5f6a7b8c9d4e5",
            commit_message="security: upgrade JWT signing from HS256 to RS256 asymmetric keys",
            author="Alex Rivera", branch="security/jwt-rs256", repo="acme/platform",
            services_affected=["auth-service", "user-service", "api-gateway"],
            cpu_at_deploy=29.0, error_rate_at_deploy=0.08, latency_at_deploy=94.0,
            status="INCIDENT", timestamp=now),
        Deployment(id="dep-005",
            commit_sha="e5f6a7b8c9d0e5f6a7b8c9d0e5f6a7b8c9d0e5f6",
            commit_message="hotfix: revert JWT RS256 -- public key not propagated to all services",
            author="Sarah Chen", branch="main", repo="acme/platform",
            services_affected=["auth-service", "user-service"],
            cpu_at_deploy=23.0, error_rate_at_deploy=0.07, latency_at_deploy=91.0,
            status="STABLE", timestamp=now),
        Deployment(id="dep-006",
            commit_sha="f6a7b8c9d0e1f6a7b8c9d0e1f6a7b8c9d0e1f6a7",
            commit_message="chore: add Datadog APM traces to payment and auth services",
            author="Marcus Kim", branch="main", repo="acme/platform",
            services_affected=["payment-service", "auth-service"],
            cpu_at_deploy=25.0, error_rate_at_deploy=0.08, latency_at_deploy=93.0,
            status="STABLE", timestamp=now),
    ]

    DEMO_INCIDENTS = [
        Incident(id="inc-001", triggered_by_deployment="dep-002", severity="P1",
            symptoms={"cpu": 92.4, "error_rate": 18.7, "latency": 3800},
            root_cause=(
                "Payment queue batch processing caused memory overflow. "
                "The 500ms flush interval accumulated too many pending transactions under load, "
                "causing the queue-worker pod to OOM. Error rate spiked to 18.7%."
            ),
            resolution=(
                "Rolled back to dep-001 (commit a1b2c3d). "
                "Payment processing returned to single-transaction mode. "
                "Memory normalised within 2 minutes."
            ),
            rolled_back_to_deployment="dep-001",
            rolled_back_to_commit="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            time_to_resolve_minutes=18, timestamp=now),
        Incident(id="inc-002", triggered_by_deployment="dep-004", severity="P1",
            symptoms={"cpu": 31.0, "error_rate": 15.2, "latency": 2100},
            root_cause=(
                "JWT RS256 upgrade failed silently. The auth-service was updated to sign tokens "
                "with RS256, but the public key was not distributed to user-service and api-gateway. "
                "All token validations failed -- 15.2% error rate across every authenticated endpoint."
            ),
            resolution=(
                "Rolled back to dep-003 -- reverted auth service to HS256. "
                "All services validated tokens again within 1 minute."
            ),
            rolled_back_to_deployment="dep-003",
            rolled_back_to_commit="c3d4e5f6a7b8c3d4e5f6a7b8c3d4e5f6a7b8c3d4",
            time_to_resolve_minutes=7, timestamp=now),
    ]

    for dep in DEMO_DEPLOYMENTS:
        try:
            await cognee_service.remember_deployment(dep)
        except Exception as e:
            logger.warning("Auto-seed deployment " + dep.id + " failed: " + str(e))

    for inc in DEMO_INCIDENTS:
        try:
            await cognee_service.remember_incident(inc)
        except Exception as e:
            logger.warning("Auto-seed incident " + inc.id + " failed: " + str(e))

    logger.info("Demo data seeded -- Quorum memory is ready.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    await cognee_service.setup()
    asyncio.create_task(metrics_simulator.broadcast_loop(2.0))
    asyncio.create_task(quorum_engine.monitor_loop())
    asyncio.create_task(_auto_seed_demo_data())
    logger.info("Quorum is online.")
    yield
    logger.info("Quorum shutting down.")


app = FastAPI(title="Quorum API", version="2.0.0", lifespan=lifespan)

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

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(sources_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Quorum v2",
        "tagline": "Always knows your last agreed-upon safe state.",
    }

@app.get("/health")
async def health():
    return {"status": "ok", "mode": metrics_simulator.current_mode()}


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
        raise HTTPException(404, "No commits found for " + owner + "/" + repo)
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


@app.get("/api/graph")
async def get_graph(current_user: User = Depends(require_analyst)):
    return await cognee_service.get_graph_data()


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
        logger.warning("WS error: " + str(e))
    finally:
        metrics_simulator.unsubscribe(queue)
