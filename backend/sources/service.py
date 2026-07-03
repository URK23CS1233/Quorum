"""Quorum — Data Source Sync Service"""

import json
import logging
import httpx
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from db_models import DataSource
import cognee_service
from models import Deployment, Incident

logger = logging.getLogger(__name__)


async def sync_source(source: DataSource, db: Session) -> dict:
    cfg = json.loads(source.config or "{}")
    synced = 0

    try:
        if source.source_type == "github":
            synced = await _sync_github(cfg)
        elif source.source_type == "pagerduty":
            synced = await _sync_pagerduty(cfg)
        elif source.source_type == "datadog":
            synced = await _sync_datadog(cfg)
        elif source.source_type == "slack":
            synced = 0  # Slack is inbound-only (webhook)
        else:
            synced = 0

        source.last_sync = datetime.now(timezone.utc)
        source.sync_count += synced
        db.commit()
        return {"status": "ok", "synced": synced, "source": source.name}

    except Exception as e:
        logger.error(f"Source sync failed [{source.name}]: {e}")
        return {"status": "error", "message": str(e), "source": source.name}


async def _sync_github(cfg: dict) -> int:
    from github_service import fetch_recent_commits
    owner = cfg.get("owner", "")
    repo  = cfg.get("repo", "")
    token = cfg.get("token", "")
    if not (owner and repo):
        return 0
    deps = await fetch_recent_commits(owner, repo, limit=cfg.get("limit", 10))
    for dep in deps:
        await cognee_service.remember_deployment(dep)
    return len(deps)


async def _sync_pagerduty(cfg: dict) -> int:
    api_key = cfg.get("api_key", "")
    if not api_key:
        return 0
    headers = {"Authorization": f"Token token={api_key}", "Accept": "application/vnd.pagerduty+json;version=2"}
    url = "https://api.pagerduty.com/incidents?statuses[]=resolved&limit=10&sort_by=resolved_at:desc"
    count = 0
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            for inc_data in r.json().get("incidents", []):
                inc = Incident(
                    triggered_by_deployment="pagerduty-import",
                    symptoms={"source": "pagerduty", "urgency": inc_data.get("urgency", "low")},
                    root_cause=inc_data.get("description", "PagerDuty incident"),
                    resolution=f"Status: {inc_data.get('status', 'resolved')}",
                    rolled_back_to_deployment="unknown",
                    rolled_back_to_commit="unknown",
                    time_to_resolve_minutes=_pd_ttr(inc_data),
                    severity="P1" if inc_data.get("urgency") == "high" else "P2",
                )
                await cognee_service.remember_incident(inc)
                count += 1
        except Exception as e:
            logger.warning(f"PagerDuty sync failed: {e}")
    return count


def _pd_ttr(inc: dict) -> int:
    try:
        created = datetime.fromisoformat(inc["created_at"].replace("Z", "+00:00"))
        resolved = datetime.fromisoformat(inc["resolved_at"].replace("Z", "+00:00"))
        return max(1, int((resolved - created).total_seconds() / 60))
    except Exception:
        return 10


async def _sync_datadog(cfg: dict) -> int:
    api_key = cfg.get("api_key", "")
    app_key = cfg.get("app_key", "")
    if not (api_key and app_key):
        return 0
    # Datadog metrics would be ingested here — for demo, ingest as deployment context
    logger.info("Datadog sync: simulated (add real metric queries as needed)")
    return 0
