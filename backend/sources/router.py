"""Quorum — Data Sources Router"""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from dependencies import require_operator, require_analyst, get_current_user
from db_models import DataSource, User, AuditLog
from sources.service import sync_source

router = APIRouter(prefix="/api/sources", tags=["sources"])

SOURCE_TYPES = ["github", "pagerduty", "datadog", "slack", "manual"]


class CreateSourceRequest(BaseModel):
    name: str
    source_type: str
    config: Optional[dict] = {}


class UpdateSourceRequest(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None


def _source_out(s: DataSource) -> dict:
    cfg = json.loads(s.config or "{}")
    # Redact sensitive fields
    safe_cfg = {k: ("***" if k in ("token", "api_key", "app_key", "webhook_url") else v)
                for k, v in cfg.items()}
    return {
        "id": s.id, "name": s.name, "source_type": s.source_type,
        "is_active": s.is_active, "sync_count": s.sync_count,
        "last_sync": str(s.last_sync) if s.last_sync else None,
        "created_at": str(s.created_at),
        "config_preview": safe_cfg,
    }


@router.get("/", response_model=List[dict])
async def list_sources(
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    sources = db.query(DataSource).filter(DataSource.org_id == current_user.org_id).all()
    return [_source_out(s) for s in sources]


@router.post("/", response_model=dict, status_code=201)
async def create_source(
    body: CreateSourceRequest,
    current_user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    if body.source_type not in SOURCE_TYPES:
        raise HTTPException(400, f"source_type must be one of: {SOURCE_TYPES}")

    s = DataSource(
        org_id=current_user.org_id, name=body.name,
        source_type=body.source_type,
        config=json.dumps(body.config or {}),
        created_by=current_user.id,
    )
    db.add(s)
    db.add(AuditLog(
        user_id=current_user.id, action="source.create",
        resource=body.name, details=body.source_type,
    ))
    db.commit(); db.refresh(s)
    return _source_out(s)


@router.patch("/{source_id}", response_model=dict)
async def update_source(
    source_id: str,
    body: UpdateSourceRequest,
    current_user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    s = db.query(DataSource).filter(
        DataSource.id == source_id, DataSource.org_id == current_user.org_id
    ).first()
    if not s:
        raise HTTPException(404, "Source not found")
    if body.name is not None:      s.name = body.name
    if body.is_active is not None: s.is_active = body.is_active
    if body.config is not None:
        # Merge config (don't wipe existing keys not sent)
        existing = json.loads(s.config or "{}")
        existing.update(body.config)
        s.config = json.dumps(existing)
    db.commit(); db.refresh(s)
    return _source_out(s)


@router.delete("/{source_id}")
async def delete_source(
    source_id: str,
    current_user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    s = db.query(DataSource).filter(
        DataSource.id == source_id, DataSource.org_id == current_user.org_id
    ).first()
    if not s:
        raise HTTPException(404, "Source not found")
    db.delete(s)
    db.add(AuditLog(user_id=current_user.id, action="source.delete", resource=s.name))
    db.commit()
    return {"status": "ok"}


@router.post("/{source_id}/sync")
async def trigger_sync(
    source_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    s = db.query(DataSource).filter(
        DataSource.id == source_id, DataSource.org_id == current_user.org_id
    ).first()
    if not s:
        raise HTTPException(404, "Source not found")

    background_tasks.add_task(sync_source, s, db)
    return {"status": "ok", "message": f"Sync triggered for {s.name}"}
