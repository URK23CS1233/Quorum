"""Unit tests for the data-source sync service."""

import json
from unittest.mock import AsyncMock

import pytest

import sources.service as ss
import cognee_service
from db_models import DataSource, Organization
from models import Deployment


def _dep(i):
    return Deployment(
        id=f"dep-{i}", commit_sha=f"sha{i}", commit_message="m", author="a",
        services_affected=["api"], cpu_at_deploy=1.0,
        error_rate_at_deploy=0.0, latency_at_deploy=1.0,
    )


def _source(db, source_type="github", config=None):
    org = Organization(name="O", slug=f"o-{source_type}")
    db.add(org); db.flush()
    s = DataSource(org_id=org.id, name=f"{source_type}-src",
                   source_type=source_type, config=json.dumps(config or {}))
    db.add(s); db.commit(); db.refresh(s)
    return s


# ── _pd_ttr ───────────────────────────────────────────────────────
def test_pd_ttr_valid():
    inc = {"created_at": "2024-01-01T00:00:00Z", "resolved_at": "2024-01-01T00:30:00Z"}
    assert ss._pd_ttr(inc) == 30


def test_pd_ttr_invalid_defaults_to_10():
    assert ss._pd_ttr({}) == 10


# ── sync_source: github ───────────────────────────────────────────
async def test_sync_source_github(monkeypatch, db_session):
    import github_service
    monkeypatch.setattr(github_service, "fetch_recent_commits",
                        AsyncMock(return_value=[_dep(1), _dep(2)]))
    remembered = []
    monkeypatch.setattr(cognee_service, "remember_deployment",
                        AsyncMock(side_effect=lambda d: remembered.append(d)))

    src = _source(db_session, "github", {"owner": "o", "repo": "r"})
    result = await ss.sync_source(src, db_session)

    assert result["status"] == "ok"
    assert result["synced"] == 2
    assert len(remembered) == 2
    assert src.sync_count == 2
    assert src.last_sync is not None


async def test_sync_github_missing_owner_repo_returns_zero():
    assert await ss._sync_github({"owner": ""}) == 0


# ── sync_source: other types ──────────────────────────────────────
async def test_sync_source_unknown_type(db_session):
    src = _source(db_session, "manual")
    result = await ss.sync_source(src, db_session)
    assert result["status"] == "ok"
    assert result["synced"] == 0


async def test_sync_source_slack_is_inbound_only(db_session):
    src = _source(db_session, "slack")
    result = await ss.sync_source(src, db_session)
    assert result["synced"] == 0


async def test_sync_source_error_path(monkeypatch, db_session):
    monkeypatch.setattr(ss, "_sync_github", AsyncMock(side_effect=RuntimeError("boom")))
    src = _source(db_session, "github", {"owner": "o", "repo": "r"})
    result = await ss.sync_source(src, db_session)
    assert result["status"] == "error"
    assert "boom" in result["message"]


# ── pagerduty / datadog guards ────────────────────────────────────
async def test_sync_pagerduty_missing_key():
    assert await ss._sync_pagerduty({}) == 0


async def test_sync_datadog_missing_keys():
    assert await ss._sync_datadog({"api_key": "only-one"}) == 0


async def test_sync_pagerduty_ingests_incidents(monkeypatch):
    import httpx

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"incidents": [
                {"urgency": "high", "description": "DB outage", "status": "resolved",
                 "created_at": "2024-01-01T00:00:00Z", "resolved_at": "2024-01-01T00:10:00Z"},
            ]}

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, headers=None):
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    remembered = []
    monkeypatch.setattr(cognee_service, "remember_incident",
                        AsyncMock(side_effect=lambda i: remembered.append(i)))

    count = await ss._sync_pagerduty({"api_key": "pd-key"})
    assert count == 1
    assert remembered[0].severity == "P1"      # high urgency -> P1
