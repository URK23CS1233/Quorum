"""
Quorum Demo Data Seeder
Pre-loads Quorum's memory with a rich, coherent production history:
~50 deployments and ~18 resolved incidents across many services, so the
Deployment Timeline, Incident history and rollback recommendations look real.

The memory endpoints are auth-gated (OPERATOR+), so this script registers (or
logs into) a dedicated seed account and sends a bearer token with every request.

Usage (backend must be running on :8080):
    python seed_incidents.py
"""

import asyncio
import hashlib
import sys
from datetime import datetime, timedelta, timezone

import httpx

# Windows consoles default to cp1252, which can't encode the emoji below.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

API = "http://localhost:8080"

SEED_USER = {
    "name": "Seed Bot",
    "email": "seed@quorum.io",
    "password": "SeedPass1234",
    "org_name": "Acme Platform",
}

AUTHORS = [
    "Sarah Chen", "Marcus Kim", "Alex Rivera", "Priya Nair", "Diego Santos",
    "Lena Novak", "Tom Fitzgerald", "Aisha Bello", "Yuki Tanaka", "Omar Haddad",
]


def _sha(seed: str) -> str:
    return hashlib.sha1(seed.encode()).hexdigest()  # realistic 40-char hex


# ── Incident scenarios: each yields a bad deploy → incident → fix deploy ──────
SCENARIOS = [
    {
        "services": ["payment-service", "queue-worker"],
        "bad": "feat: switch payment queue to batch processing (500ms flush)",
        "fix": "revert: undo payment queue batching — OOM under load",
        "symptoms": {"cpu": 92.4, "error_rate": 18.7, "latency": 3800},
        "severity": "P1", "ttr": 18,
        "root_cause": "The 500ms flush interval accumulated too many pending transactions "
                      "under load, OOM-ing the queue-worker. Cascading failures hit "
                      "payment-service as it could not enqueue. Error rate hit 18.7%. "
                      "Root cause: unbounded in-memory queue growth under concurrency.",
        "resolution": "Rolled back to the pre-batching stable state; payment processing "
                      "returned to single-transaction mode and memory normalised in 2 min.",
    },
    {
        "services": ["auth-service", "user-service", "api-gateway"],
        "bad": "security: upgrade JWT signing from HS256 to RS256 asymmetric keys",
        "fix": "hotfix: revert JWT RS256 — public key not propagated to all services",
        "symptoms": {"cpu": 31.0, "error_rate": 15.2, "latency": 2100},
        "severity": "P1", "ttr": 7,
        "root_cause": "auth-service began signing tokens with RS256 but the public key was "
                      "never distributed to user-service and api-gateway. Every token "
                      "validation failed, causing a 401 cascade across all authed endpoints.",
        "resolution": "Reverted auth-service to HS256; all services could validate tokens "
                      "again within 1 minute. Follow-up: build a key-distribution pipeline.",
    },
    {
        "services": ["cache-layer", "product-service"],
        "bad": "perf: add Redis caching for product catalog (no jitter on TTL)",
        "fix": "fix: add TTL jitter + request coalescing to prevent cache stampede",
        "symptoms": {"cpu": 88.0, "error_rate": 9.4, "latency": 4200},
        "severity": "P1", "ttr": 22,
        "root_cause": "All catalog cache keys were given an identical TTL. On mass expiry "
                      "every request stampeded the database simultaneously (thundering herd), "
                      "saturating the connection pool and blowing p99 latency to 4.2s.",
        "resolution": "Added ±10% TTL jitter and single-flight request coalescing; DB load "
                      "dropped 80% and latency returned to ~95ms.",
    },
    {
        "services": ["database-layer", "order-service"],
        "bad": "migration: add index on orders.customer_id (blocking ALTER)",
        "fix": "migration: rebuild index CONCURRENTLY to avoid write lock",
        "symptoms": {"cpu": 45.0, "error_rate": 22.1, "latency": 5600},
        "severity": "P1", "ttr": 14,
        "root_cause": "A blocking ALTER TABLE took an ACCESS EXCLUSIVE lock on the orders "
                      "table for 6 minutes. All order writes queued and timed out; checkout "
                      "error rate spiked to 22%.",
        "resolution": "Aborted the migration and re-ran it with CREATE INDEX CONCURRENTLY, "
                      "which does not block writes. Orders resumed immediately.",
    },
    {
        "services": ["notification-service"],
        "bad": "feat: real-time notifications over persistent WebSockets",
        "fix": "fix: close leaked WebSocket handles + cap connections per pod",
        "symptoms": {"cpu": 79.0, "error_rate": 6.1, "latency": 1900},
        "severity": "P2", "ttr": 40,
        "root_cause": "WebSocket handles were never closed on client disconnect. Memory and "
                      "file descriptors leaked steadily over ~3 hours until pods hit their "
                      "FD limit and refused new connections.",
        "resolution": "Added disconnect handlers and a per-pod connection cap; recycled the "
                      "leaking pods. Memory growth flattened.",
    },
    {
        "services": ["api-gateway", "rate-limiter"],
        "bad": "chore: tighten global rate limit to 50 req/min per IP",
        "fix": "fix: raise limit + exempt internal service-to-service traffic",
        "symptoms": {"cpu": 34.0, "error_rate": 27.8, "latency": 320},
        "severity": "P1", "ttr": 9,
        "root_cause": "The new 50 req/min cap also applied to internal service-to-service "
                      "calls behind a shared NAT IP. Internal traffic was throttled to 429s, "
                      "breaking nearly every downstream call.",
        "resolution": "Raised the public limit and exempted internal CIDR ranges from the "
                      "limiter. 429 rate returned to baseline.",
    },
    {
        "services": ["order-service", "database-layer"],
        "bad": "perf: increase DB connection pool workers to 200",
        "fix": "fix: cap pool at 60 + add PgBouncer in front of Postgres",
        "symptoms": {"cpu": 71.0, "error_rate": 12.6, "latency": 3100},
        "severity": "P1", "ttr": 16,
        "root_cause": "Raising each pod's pool to 200 × 12 pods exceeded Postgres "
                      "max_connections (250). New connections were refused, causing "
                      "'too many clients' errors across order-service.",
        "resolution": "Capped the per-pod pool and introduced PgBouncer transaction pooling; "
                      "connection count dropped under the ceiling.",
    },
    {
        "services": ["checkout-service", "feature-flags"],
        "bad": "feat: roll new one-click checkout to 100% of traffic",
        "fix": "revert: gate one-click checkout back to 5% canary",
        "symptoms": {"cpu": 40.0, "error_rate": 19.3, "latency": 900},
        "severity": "P1", "ttr": 11,
        "root_cause": "The one-click checkout flow assumed a saved payment method always "
                      "existed. For guests it threw a null-reference and 500'd the whole "
                      "checkout for ~19% of sessions.",
        "resolution": "Flipped the flag back to a 5% canary and shipped a guard for the "
                      "guest path. Checkout success recovered.",
    },
    {
        "services": ["cdn-edge", "api-gateway"],
        "bad": "perf: cache API responses at the CDN edge (missing Vary header)",
        "fix": "fix: add Vary: Authorization + bypass cache for authed routes",
        "symptoms": {"cpu": 22.0, "error_rate": 8.8, "latency": 140},
        "severity": "P2", "ttr": 25,
        "root_cause": "Authenticated API responses were cached at the edge without a "
                      "Vary: Authorization header, so users were served other users' cached "
                      "personalised data — a correctness and privacy incident.",
        "resolution": "Added Vary: Authorization and excluded authed routes from edge "
                      "caching; purged the poisoned cache.",
    },
    {
        "services": ["search-service"],
        "bad": "feat: faceted search with per-facet aggregation query",
        "fix": "perf: batch facet counts into a single aggregation query",
        "symptoms": {"cpu": 84.0, "error_rate": 3.2, "latency": 6100},
        "severity": "P2", "ttr": 33,
        "root_cause": "Each search issued one aggregation query per facet (N+1). Popular "
                      "queries with 20 facets fired 20 sequential DB round-trips, pushing "
                      "p99 latency past 6 seconds.",
        "resolution": "Collapsed the facet counts into a single grouped aggregation; latency "
                      "fell back to ~180ms.",
    },
    {
        "services": ["inventory-service"],
        "bad": "feat: optimistic inventory decrement without row lock",
        "fix": "fix: use SELECT ... FOR UPDATE to prevent oversell",
        "symptoms": {"cpu": 38.0, "error_rate": 5.5, "latency": 260},
        "severity": "P1", "ttr": 20,
        "root_cause": "Concurrent purchases read the same stock count and both decremented, "
                      "overselling limited-stock items. A flash sale oversold 1,400 units.",
        "resolution": "Added row-level locking (SELECT FOR UPDATE) on the stock row; oversell "
                      "stopped immediately.",
    },
    {
        "services": ["cart-service"],
        "bad": "refactor: rewrite cart merge logic for guest→user login",
        "fix": "hotfix: null-guard empty guest cart on merge",
        "symptoms": {"cpu": 26.0, "error_rate": 11.0, "latency": 180},
        "severity": "P2", "ttr": 6,
        "root_cause": "Merging a guest cart into a user account NPE'd when the guest cart was "
                      "empty, 500-ing login for anyone with no active cart.",
        "resolution": "Added a null/empty guard on the merge path. Login errors cleared.",
    },
    {
        "services": ["recommendation-service"],
        "bad": "feat: real-time recommendations with 10k-item batch scoring",
        "fix": "fix: stream scoring in 256-item chunks to bound memory",
        "symptoms": {"cpu": 90.0, "error_rate": 4.0, "latency": 2600},
        "severity": "P2", "ttr": 28,
        "root_cause": "Scoring 10k candidate items in a single in-memory batch OOM-killed the "
                      "recommendation pods during peak traffic.",
        "resolution": "Switched to chunked streaming inference (256 items); memory stayed "
                      "bounded and pods stopped crashing.",
    },
    {
        "services": ["api-gateway"],
        "bad": "chore: lower upstream timeout to 500ms across the gateway",
        "fix": "fix: restore 3s timeout + add per-route budgets",
        "symptoms": {"cpu": 33.0, "error_rate": 24.5, "latency": 520},
        "severity": "P1", "ttr": 8,
        "root_cause": "A blanket 500ms upstream timeout was shorter than the payment "
                      "provider's typical 800ms response, so every payment call 504'd and "
                      "retried, amplifying load.",
        "resolution": "Restored a 3s default and set per-route timeout budgets. 504s cleared.",
    },
    {
        "services": ["order-service", "payment-service"],
        "bad": "feat: retry failed charges automatically (no idempotency key)",
        "fix": "fix: attach idempotency key to every charge attempt",
        "symptoms": {"cpu": 29.0, "error_rate": 7.7, "latency": 410},
        "severity": "P1", "ttr": 15,
        "root_cause": "Automatic charge retries lacked an idempotency key, so transient "
                      "timeouts double-charged customers. 300+ duplicate charges before "
                      "detection.",
        "resolution": "Added a deterministic idempotency key per order; the provider now "
                      "dedupes retries. Issued refunds for duplicates.",
    },
    {
        "services": ["cache-layer"],
        "bad": "chore: set default cache TTL to 0 (always fresh)",
        "fix": "revert: restore 300s cache TTL",
        "symptoms": {"cpu": 76.0, "error_rate": 2.1, "latency": 2200},
        "severity": "P2", "ttr": 12,
        "root_cause": "A config typo set TTL=0, disabling caching entirely. Every request "
                      "fell through to origin, tripling DB load and doubling latency.",
        "resolution": "Restored the 300s TTL. Cache hit-rate and latency recovered within a "
                      "minute.",
    },
    {
        "services": ["user-service", "notification-service"],
        "bad": "feat: resend verification email on every failed login",
        "fix": "fix: rate-limit verification emails to 1 per 15 min",
        "symptoms": {"cpu": 41.0, "error_rate": 1.4, "latency": 300},
        "severity": "P3", "ttr": 45,
        "root_cause": "A retry loop resent the verification email on each failed login. Bots "
                      "hammering credentials triggered an email flood and got the domain "
                      "temporarily blocklisted by the mail provider.",
        "resolution": "Added a 15-minute per-user cooldown on verification emails and "
                      "de-listed the domain.",
    },
    {
        "services": ["logging-pipeline", "api-gateway"],
        "bad": "chore: enable DEBUG logging in production for a repro",
        "fix": "revert: set log level back to INFO + rotate volumes",
        "symptoms": {"cpu": 52.0, "error_rate": 13.9, "latency": 1600},
        "severity": "P2", "ttr": 19,
        "root_cause": "DEBUG logging was left on after a debugging session. Log volume "
                      "filled the node disks; pods that could not write logs crash-looped.",
        "resolution": "Reset log level to INFO, rotated and expanded log volumes, and added "
                      "a disk-usage alert.",
    },
]

# ── Standalone stable feature deployments (no incident) ───────────────────────
STABLE_FEATURES = [
    ("feat: add dark mode to the operator dashboard", ["web-frontend"]),
    ("chore: upgrade Next.js 13 → 14 and enable app router", ["web-frontend"]),
    ("feat: CSV export for the deployment timeline", ["web-frontend", "api-gateway"]),
    ("ops: add /health and /ready probes to every service", ["api-gateway"]),
    ("obs: export Prometheus metrics from payment-service", ["payment-service"]),
    ("perf: lazy-load product images with responsive srcset", ["web-frontend"]),
    ("feat: cursor pagination for the orders API", ["order-service"]),
    ("refactor: extract shared auth middleware into a library", ["auth-service", "api-gateway"]),
    ("feat: exponential-backoff retries for outbound webhooks", ["notification-service"]),
    ("i18n: add Spanish and Japanese translations", ["web-frontend"]),
    ("perf: warm the product-catalog cache on deploy", ["cache-layer", "product-service"]),
    ("feat: A/B testing framework with sticky bucketing", ["feature-flags"]),
    ("chore: bump Postgres driver to 16.2 for prepared-stmt fix", ["database-layer"]),
    ("feat: SSO login via Google and GitHub OAuth", ["auth-service"]),
    ("perf: enable HTTP/2 and Brotli at the edge", ["cdn-edge"]),
    ("feat: add audit log export for compliance", ["api-gateway"]),
]


def build_dataset():
    deployments, incidents = [], []
    counter = 0
    # oldest-first timeline ending a few days ago
    cursor = datetime.now(timezone.utc) - timedelta(days=112)

    def add_dep(msg, services, status, idx):
        nonlocal counter, cursor
        counter += 1
        did = f"dep-{counter:03d}"
        sha = _sha(did + msg)
        cursor += timedelta(hours=44, minutes=(counter * 7) % 60)
        deployments.append({
            "id": did,
            "commit_sha": sha,
            "commit_message": msg,
            "author": AUTHORS[idx % len(AUTHORS)],
            "services_affected": services,
            "cpu_at_deploy": round(22.0 + (counter * 1.7) % 11, 1),
            "error_rate_at_deploy": round(0.05 + (counter % 6) * 0.01, 3),
            "latency_at_deploy": round(84.0 + (counter * 3) % 26, 1),
            "status": status,
            "branch": "main" if status == "STABLE" else f"feature/{services[0]}",
            "repo": "acme/platform",
            "timestamp": cursor.isoformat(),
        })
        return did, sha

    last_stable = None
    inc_counter = 0
    for i, sc in enumerate(SCENARIOS):
        # interleave a clean feature deploy before some incidents
        if i < len(STABLE_FEATURES):
            fmsg, fsvc = STABLE_FEATURES[i]
            sid, ssha = add_dep(fmsg, fsvc, "STABLE", i)
            last_stable = (sid, ssha)

        bid, _ = add_dep(sc["bad"], sc["services"], "INCIDENT", i + 1)
        rb_id, rb_sha = last_stable or (bid, _sha(bid))

        inc_counter += 1
        incidents.append({
            "id": f"inc-{inc_counter:03d}",
            "triggered_by_deployment": bid,
            "symptoms": sc["symptoms"],
            "root_cause": sc["root_cause"],
            "resolution": sc["resolution"],
            "rolled_back_to_deployment": rb_id,
            "rolled_back_to_commit": rb_sha,
            "time_to_resolve_minutes": sc["ttr"],
            "severity": sc["severity"],
        })

        # the fix/revert deploy becomes the new stable baseline
        fid, fsha = add_dep(sc["fix"], sc["services"], "STABLE", i + 2)
        last_stable = (fid, fsha)

    # any remaining stable features go on the end as recent clean deploys
    for j, (fmsg, fsvc) in enumerate(STABLE_FEATURES[len(SCENARIOS):], start=1):
        add_dep(fmsg, fsvc, "STABLE", j)

    return deployments, incidents


async def get_token(client: httpx.AsyncClient) -> str:
    r = await client.post(f"{API}/api/auth/register", json=SEED_USER)
    if r.status_code == 201:
        return r.json()["access_token"]
    # account already exists -> log in
    r = await client.post(f"{API}/api/auth/login",
                          json={"email": SEED_USER["email"], "password": SEED_USER["password"]})
    r.raise_for_status()
    return r.json()["access_token"]


async def seed():
    deployments, incidents = build_dataset()
    async with httpx.AsyncClient(timeout=120.0) as client:
        print("\n🔒 Quorum Demo Seeder")
        print("=" * 52)
        token = await get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        print(f"✓ authenticated as {SEED_USER['email']}")

        print(f"\n📦 Seeding {len(deployments)} deployments...")
        ok = 0
        for dep in deployments:
            r = await client.post(f"{API}/api/memory/deployment",
                                  json={"deployment": dep}, headers=headers)
            if r.status_code == 200:
                ok += 1
                print(f"  ✓ {dep['id']} [{dep['status']:8}] {dep['commit_message'][:52]}")
            else:
                print(f"  ✗ {dep['id']} failed ({r.status_code}): {r.text[:120]}")
        print(f"   → {ok}/{len(deployments)} deployments stored")

        print(f"\n🚨 Seeding {len(incidents)} resolved incidents...")
        iok = 0
        for inc in incidents:
            r = await client.post(f"{API}/api/memory/incident",
                                  json={"incident": inc}, headers=headers)
            if r.status_code == 200:
                iok += 1
                print(f"  ✓ {inc['id']} [{inc['severity']}] rollback→{inc['rolled_back_to_deployment']}")
            else:
                print(f"  ✗ {inc['id']} failed ({r.status_code}): {r.text[:120]}")
        print(f"   → {iok}/{len(incidents)} incidents stored")

        print("\n✅ Quorum memory seeded!")
        print("─── DEMO ────────────────────────────────────────────")
        print("1. Open http://localhost:3000  (log out/in if needed)")
        print("2. Deployment Timeline now shows the full history")
        print("3. Simulate → Error Storm, watch Quorum recommend a safe state")
        print("4. Confirm Rollback — Quorum records the resolution")
        print("─────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    asyncio.run(seed())
