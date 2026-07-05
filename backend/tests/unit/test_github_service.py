"""Unit tests for the GitHub ingestion service."""

import httpx
import pytest

import github_service as gh


# ── pure helpers ──────────────────────────────────────────────────
@pytest.mark.parametrize("files,expected", [
    (["src/payment/api.py"], {"payment-service", "api-gateway"}),
    (["auth/login.py"], {"auth-service"}),
    (["k8s/deploy.yaml"], {"kubernetes-config"}),
    (["README.md"], {"core-service"}),        # no keyword match -> default
    ([], {"core-service"}),
])
def test_infer_services(files, expected):
    assert set(gh._infer_services(files)) == expected


def test_estimate_cpu_scales_with_files():
    assert gh._estimate_cpu([]) == 25.0
    assert gh._estimate_cpu(["a"]) == 25.8
    # capped at +20
    many = [f"f{i}" for i in range(100)]
    assert gh._estimate_cpu(many) == 45.0


def test_headers_include_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")
    h = gh._headers()
    assert h["Authorization"] == "Bearer ghp_secret"
    assert h["Accept"] == "application/vnd.github+json"


def test_headers_without_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "")
    assert "Authorization" not in gh._headers()


# ── fake httpx client ─────────────────────────────────────────────
class _FakeResp:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=None)


def _install_fake_client(monkeypatch, *, list_data, detail_data=None,
                         list_raises=False, detail_raises=False):
    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, headers=None):
            if "per_page" in url:              # commit list request
                if list_raises:
                    raise httpx.ConnectError("boom")
                return _FakeResp(list_data)
            # per-commit detail request
            if detail_raises:
                raise httpx.ConnectError("boom")
            return _FakeResp(detail_data or {"files": []})

    monkeypatch.setattr(gh.httpx, "AsyncClient", _FakeClient)


# ── fetch_recent_commits ──────────────────────────────────────────
async def test_fetch_recent_commits_maps_deployments(monkeypatch):
    list_data = [{
        "sha": "abc123def456",
        "commit": {
            "message": "fix payment bug\n\nlong body ignored",
            "author": {"name": "Alice", "date": "2024-01-01T00:00:00Z"},
        },
    }]
    detail_data = {"files": [{"filename": "src/payment/api.py"}]}
    _install_fake_client(monkeypatch, list_data=list_data, detail_data=detail_data)

    deps = await gh.fetch_recent_commits("owner", "repo", limit=1)
    assert len(deps) == 1
    d = deps[0]
    assert d.commit_sha == "abc123def456"
    assert d.commit_message == "fix payment bug"     # first line only
    assert d.author == "Alice"
    assert d.repo == "owner/repo"
    assert set(d.services_affected) == {"payment-service", "api-gateway"}
    assert d.status == "STABLE"


async def test_fetch_recent_commits_list_error_returns_empty(monkeypatch):
    _install_fake_client(monkeypatch, list_data=[], list_raises=True)
    assert await gh.fetch_recent_commits("o", "r") == []


async def test_fetch_recent_commits_detail_error_uses_fallback(monkeypatch):
    list_data = [{
        "sha": "deadbeef", "commit": {
            "message": "chore", "author": {"name": "Bob", "date": "2024-01-02T00:00:00Z"}},
    }]
    _install_fake_client(monkeypatch, list_data=list_data, detail_raises=True)
    deps = await gh.fetch_recent_commits("o", "r", limit=1)
    assert deps[0].services_affected == ["unknown-service"]


async def test_fetch_recent_commits_truncates_long_message(monkeypatch):
    long_msg = "x" * 200
    list_data = [{
        "sha": "s", "commit": {
            "message": long_msg, "author": {"name": "C", "date": "2024-01-03T00:00:00Z"}},
    }]
    _install_fake_client(monkeypatch, list_data=list_data, detail_data={"files": []})
    deps = await gh.fetch_recent_commits("o", "r", limit=1)
    assert len(deps[0].commit_message) == 120
