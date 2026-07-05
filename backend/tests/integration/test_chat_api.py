"""Integration tests for the chat API (SSE streaming + conversation management)."""

from db_models import UserRole


def _analyst(client, make_user):
    _user, token = make_user(role=UserRole.ANALYST)
    return {"Authorization": f"Bearer {token}"}


# ── access control ────────────────────────────────────────────────
def test_chat_requires_auth(client):
    assert client.post("/api/chat/message", json={"message": "hi"}).status_code == 401


def test_chat_rejects_viewer(client, auth_header):
    r = client.post("/api/chat/message", headers=auth_header(UserRole.VIEWER),
                    json={"message": "hi"})
    assert r.status_code == 403


# ── streaming ─────────────────────────────────────────────────────
def test_chat_stream_returns_sse(client, make_user):
    hdr = _analyst(client, make_user)
    r = client.post("/api/chat/message", headers=hdr,
                    json={"message": "why did prod break?"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    # default (stubbed) OpenAI client degrades to a graceful error frame + done
    assert "data:" in r.text
    assert "done" in r.text


def test_chat_stream_creates_conversation_and_messages(client, make_user):
    hdr = _analyst(client, make_user)
    client.post("/api/chat/message", headers=hdr, json={"message": "how to roll back?"})

    convs = client.get("/api/chat/conversations", headers=hdr).json()
    assert len(convs) == 1
    conv_id = convs[0]["id"]

    msgs = client.get(f"/api/chat/conversations/{conv_id}/messages", headers=hdr).json()
    roles = {m["role"] for m in msgs}
    assert roles == {"user", "assistant"}


# ── conversation management ───────────────────────────────────────
def test_list_conversations_empty(client, make_user):
    hdr = _analyst(client, make_user)
    assert client.get("/api/chat/conversations", headers=hdr).json() == []


def test_delete_conversation(client, make_user):
    hdr = _analyst(client, make_user)
    client.post("/api/chat/message", headers=hdr, json={"message": "hello"})
    conv_id = client.get("/api/chat/conversations", headers=hdr).json()[0]["id"]
    assert client.delete(f"/api/chat/conversations/{conv_id}", headers=hdr).status_code == 200
    assert client.get("/api/chat/conversations", headers=hdr).json() == []


def test_delete_missing_conversation_404(client, make_user):
    hdr = _analyst(client, make_user)
    assert client.delete("/api/chat/conversations/nope", headers=hdr).status_code == 404


# ── usage ─────────────────────────────────────────────────────────
def test_token_usage_stats(client, make_user):
    hdr = _analyst(client, make_user)
    r = client.get("/api/chat/usage", headers=hdr)
    assert r.status_code == 200
    body = r.json()
    for key in ("total_tokens", "total_messages", "ai_messages",
                "avg_tokens_per_msg", "estimated_cost_usd"):
        assert key in body
