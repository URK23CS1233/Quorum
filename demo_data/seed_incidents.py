"""
Quorum Demo Data Seeder
Run this AFTER starting the backend to pre-load Quorum's memory with
6 deployments and 2 incidents. This makes the demo compelling because
Quorum will recall actual past incidents when anomalies fire.

Usage:
    python seed_incidents.py
"""

import asyncio
import httpx

API = "http://localhost:8000"

DEPLOYMENTS = [
    {
        "id": "dep-001",
        "commit_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        "commit_message": "Initial production rollout — payment service v2.0",
        "author": "Sarah Chen",
        "services_affected": ["payment-service", "api-gateway"],
        "cpu_at_deploy": 24.0,
        "error_rate_at_deploy": 0.07,
        "latency_at_deploy": 88.0,
        "status": "STABLE",
        "branch": "main",
        "repo": "acme/platform",
    },
    {
        "id": "dep-002",
        "commit_sha": "b2c3d4e5f6a7b2c3d4e5f6a7b2c3d4e5f6a7b2c3",
        "commit_message": "feat: switch payment queue to batch processing (500ms flush)",
        "author": "Marcus Kim",
        "services_affected": ["payment-service", "queue-worker"],
        "cpu_at_deploy": 27.5,
        "error_rate_at_deploy": 0.09,
        "latency_at_deploy": 92.0,
        "status": "INCIDENT",
        "branch": "feature/payment-batching",
        "repo": "acme/platform",
    },
    {
        "id": "dep-003",
        "commit_sha": "c3d4e5f6a7b8c3d4e5f6a7b8c3d4e5f6a7b8c3d4",
        "commit_message": "revert: undo payment queue batch processing — OOM in prod",
        "author": "Sarah Chen",
        "services_affected": ["payment-service", "queue-worker"],
        "cpu_at_deploy": 22.0,
        "error_rate_at_deploy": 0.07,
        "latency_at_deploy": 89.0,
        "status": "STABLE",
        "branch": "main",
        "repo": "acme/platform",
    },
    {
        "id": "dep-004",
        "commit_sha": "d4e5f6a7b8c9d4e5f6a7b8c9d4e5f6a7b8c9d4e5",
        "commit_message": "security: upgrade JWT signing from HS256 to RS256 asymmetric keys",
        "author": "Alex Rivera",
        "services_affected": ["auth-service", "user-service", "api-gateway"],
        "cpu_at_deploy": 29.0,
        "error_rate_at_deploy": 0.08,
        "latency_at_deploy": 94.0,
        "status": "INCIDENT",
        "branch": "security/jwt-rs256",
        "repo": "acme/platform",
    },
    {
        "id": "dep-005",
        "commit_sha": "e5f6a7b8c9d0e5f6a7b8c9d0e5f6a7b8c9d0e5f6",
        "commit_message": "hotfix: revert JWT RS256 — public key not propagated to all services",
        "author": "Sarah Chen",
        "services_affected": ["auth-service", "user-service"],
        "cpu_at_deploy": 23.0,
        "error_rate_at_deploy": 0.07,
        "latency_at_deploy": 91.0,
        "status": "STABLE",
        "branch": "main",
        "repo": "acme/platform",
    },
    {
        "id": "dep-006",
        "commit_sha": "f6a7b8c9d0e1f6a7b8c9d0e1f6a7b8c9d0e1f6a7",
        "commit_message": "chore: add Datadog APM traces to payment and auth services",
        "author": "Marcus Kim",
        "services_affected": ["payment-service", "auth-service"],
        "cpu_at_deploy": 25.0,
        "error_rate_at_deploy": 0.08,
        "latency_at_deploy": 93.0,
        "status": "STABLE",
        "branch": "main",
        "repo": "acme/platform",
    },
]

INCIDENTS = [
    {
        "id": "inc-001",
        "triggered_by_deployment": "dep-002",
        "symptoms": {"cpu": 92.4, "error_rate": 18.7, "latency": 3800},
        "root_cause": (
            "Payment queue batch processing caused memory overflow. "
            "The 500ms flush interval accumulated too many pending transactions under load, "
            "causing the queue-worker pod to OOM. Cascading errors hit the payment-service "
            "as it could not enqueue new transactions. Error rate spiked to 18.7%. "
            "Root cause: unbounded in-memory queue growth under concurrent load."
        ),
        "resolution": (
            "Rolled back to dep-003 (commit c3d4e5f) — the pre-batching stable state. "
            "Payment processing returned to single-transaction mode. "
            "Queue worker memory usage normalised within 2 minutes of rollback."
        ),
        "rolled_back_to_deployment": "dep-001",
        "rolled_back_to_commit": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        "time_to_resolve_minutes": 18,
        "severity": "P1",
    },
    {
        "id": "inc-002",
        "triggered_by_deployment": "dep-004",
        "symptoms": {"cpu": 31.0, "error_rate": 15.2, "latency": 2100},
        "root_cause": (
            "JWT RS256 upgrade failed silently. The auth-service was updated to sign tokens "
            "with RS256, but the public key was not distributed to user-service and api-gateway. "
            "All token validations failed, causing a 401 cascade across every authenticated endpoint. "
            "Error rate: 15.2%. Users could not log in or access any protected resource."
        ),
        "resolution": (
            "Rolled back to dep-005 (hotfix commit e5f6a7b) — reverted auth service to HS256. "
            "All services could validate tokens again within 1 minute of rollback. "
            "Post-incident: implement key distribution pipeline before re-attempting RS256."
        ),
        "rolled_back_to_deployment": "dep-003",
        "rolled_back_to_commit": "c3d4e5f6a7b8c3d4e5f6a7b8c3d4e5f6a7b8c3d4",
        "time_to_resolve_minutes": 7,
        "severity": "P1",
    },
]


async def seed():
    async with httpx.AsyncClient(timeout=120.0) as client:
        print("\n🔒 Quorum Demo Seeder")
        print("=" * 50)

        print("\n📦 Seeding deployments into Quorum memory...")
        for dep in DEPLOYMENTS:
            r = await client.post(f"{API}/api/memory/deployment", json={"deployment": dep})
            if r.status_code == 200:
                print(f"  ✓ dep-{dep['id'][-3:]}: {dep['commit_message'][:50]}…")
            else:
                print(f"  ✗ Failed: {r.text}")

        print("\n🚨 Seeding incidents into Quorum memory...")
        for inc in INCIDENTS:
            r = await client.post(f"{API}/api/memory/incident", json={"incident": inc})
            if r.status_code == 200:
                print(f"  ✓ {inc['id']}: P{inc['severity'][-1]} — {inc['root_cause'][:50]}…")
            else:
                print(f"  ✗ Failed: {r.text}")

        print("\n✅ Quorum memory seeded!")
        print("\n─── DEMO STEPS ───────────────────────────────────")
        print("1. Open http://localhost:3000")
        print("2. Click Simulate → Error Storm")
        print("3. Watch metrics go critical (red gauges)")
        print("4. Quorum fires in ~6 seconds — check Incident Panel")
        print("5. See the safe state (dep-001 or dep-003) surface")
        print("6. Click 'Confirm Rollback' — metrics recover")
        print("7. Switch to Knowledge Graph tab — see Cognee memory")
        print("──────────────────────────────────────────────────\n")


if __name__ == "__main__":
    asyncio.run(seed())
