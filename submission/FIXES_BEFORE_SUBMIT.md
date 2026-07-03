# 5 Fixes Before July 5 — Do These NOW

## Fix 1: Rate limiting on auth (15 min)
```bash
pip install slowapi
echo "slowapi==0.1.9" >> backend/requirements.txt
```

In `backend/main.py` add after imports:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

In `backend/auth/router.py`, add to login:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    ...
```

---

## Fix 2: Persist deployment registry (20 min)
In `backend/cognee_service.py`, replace the in-memory dict with SQLite reads:

```python
# Remove the global dict entirely.
# Instead, call the DB every time:

from database import SessionLocal
from db_models import AuditLog  # reuse or create a DeploymentRecord model

# For the hackathon: just use a simple JSON file as persistence
import json, pathlib

REGISTRY_FILE = pathlib.Path("deployment_registry.json")

def _load_registry() -> dict:
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text())
    return {}

def _save_registry(registry: dict):
    REGISTRY_FILE.write_text(json.dumps(registry, default=str))

# Replace _deployment_registry[dep.id] = dep  with:
# reg = _load_registry(); reg[dep.id] = dep.dict(); _save_registry(reg)
```

---

## Fix 3: Write 2 basic tests (20 min)
Create `backend/test_auth.py`:
```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_register_and_login():
    # Register
    r = client.post("/api/auth/register", json={
        "name": "Test User",
        "email": "test@example.com", 
        "password": "testpass123",
        "org_name": "Test Org"
    })
    assert r.status_code == 200
    assert "access_token" in r.json()

def test_login_wrong_password():
    r = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword"
    })
    assert r.status_code == 401

def test_protected_route_without_token():
    r = client.get("/api/users/")
    assert r.status_code == 403
```

Run with: `cd backend && pip install pytest httpx && pytest test_auth.py -v`

---

## Fix 4: Add security headers (5 min)
In `backend/main.py`, add after CORS middleware:
```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

---

## Fix 5: Document the localStorage JWT limitation
In `README.md` under "Security Notes" add:
```markdown
## Security Notes

**Authentication:** This demo uses localStorage for JWT storage for simplicity. 
Production deployment should use httpOnly cookies with SameSite=Strict to prevent XSS token theft.

**Rate limiting:** Auth endpoints are rate-limited to 10 requests/minute per IP.

**Database:** SQLite is used by default. Set DATABASE_URL to a PostgreSQL URI for production.
```

This turns a flaw into a sign of awareness — much better than leaving it undocumented.

---

## What still needs months of work (be honest with investors)

- Alembic database migrations
- httpOnly cookie auth (replace localStorage)
- Redis for session store + background job queue
- Celery workers for Cognee ingestion (currently blocks request thread)
- Proper secrets management (HashiCorp Vault / AWS Secrets Manager)
- Test coverage >80%
- SOC2 compliance for enterprise sales
- Kubernetes deployment manifests
- Monitoring + alerting (the irony: Quorum needs a Quorum for itself)
