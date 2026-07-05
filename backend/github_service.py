"""
Quorum — GitHub Integration Service
Ingests real commit history from any GitHub repo into Quorum's memory.
"""

import httpx
import os
import logging
from models import Deployment

logger = logging.getLogger(__name__)
GITHUB_API = "https://api.github.com"


def _headers() -> dict:
    token = os.getenv("GITHUB_TOKEN", "")
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


async def fetch_recent_commits(owner: str, repo: str, limit: int = 10) -> list[Deployment]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/commits?per_page={limit}"
    deployments = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url, headers=_headers())
            resp.raise_for_status()
            commits = resp.json()
        except Exception as e:
            logger.error(f"GitHub API error: {e}")
            return []

        for c in commits:
            sha    = c["sha"]
            msg    = c["commit"]["message"].split("\n")[0][:120]
            author = c["commit"]["author"]["name"]
            ts     = c["commit"]["author"]["date"]

            files = []
            try:
                detail = await client.get(
                    f"{GITHUB_API}/repos/{owner}/{repo}/commits/{sha}",
                    headers=_headers()
                )
                files    = [f["filename"] for f in detail.json().get("files", [])]
                services = _infer_services(files)
            except Exception:
                services = ["unknown-service"]

            deployments.append(Deployment(
                commit_sha=sha, commit_message=msg, author=author,
                timestamp=ts, services_affected=services,
                cpu_at_deploy=_estimate_cpu(files),
                error_rate_at_deploy=0.08, latency_at_deploy=95.0,
                status="STABLE", branch="main", repo=f"{owner}/{repo}",
            ))

    logger.info(f"Fetched {len(deployments)} commits from {owner}/{repo}")
    return deployments


def _infer_services(files: list[str]) -> list[str]:
    services = set()
    mapping = {
        "payment": "payment-service", "auth": "auth-service",
        "user": "user-service", "order": "order-service",
        "notif": "notification-service", "queue": "queue-worker",
        "api": "api-gateway", "db": "database-layer",
        "infra": "infrastructure", "k8s": "kubernetes-config",
    }
    for f in files:
        for kw, svc in mapping.items():
            if kw in f.lower():
                services.add(svc)
    return list(services) if services else ["core-service"]


def _estimate_cpu(files: list[str]) -> float:
    return round(25.0 + min(len(files) * 0.8, 20.0), 1)
