"""Unit tests for the AI chat service."""

import types

import pytest

import chat.service as chat
import auth.service as auth_svc
from db_models import User, Organization, Conversation, Message, UserRole


def _user(db):
    org = Organization(name="O", slug="o")
    db.add(org); db.flush()
    u = User(name="A", email="chat@quorum.test",
             hashed_password=auth_svc.hash_password("password123"),
             org_id=org.id, role=UserRole.ANALYST)
    db.add(u); db.commit(); db.refresh(u)
    return u


# ── conversation management ───────────────────────────────────────
def test_get_or_create_conversation_creates_new(db_session):
    u = _user(db_session)
    conv = chat.get_or_create_conversation(u.id, None, db_session)
    assert conv.id is not None
    assert conv.user_id == u.id


def test_get_or_create_conversation_returns_existing(db_session):
    u = _user(db_session)
    conv = chat.get_or_create_conversation(u.id, None, db_session)
    same = chat.get_or_create_conversation(u.id, conv.id, db_session)
    assert same.id == conv.id


def test_get_or_create_conversation_wrong_user_creates_new(db_session):
    u = _user(db_session)
    conv = chat.get_or_create_conversation(u.id, None, db_session)
    other = chat.get_or_create_conversation("someone-else", conv.id, db_session)
    assert other.id != conv.id


def test_list_conversations(db_session):
    u = _user(db_session)
    conv = chat.get_or_create_conversation(u.id, None, db_session)
    db_session.add(Message(conversation_id=conv.id, role="user", content="hello there"))
    db_session.commit()
    convs = chat.list_conversations(u.id, db_session)
    assert len(convs) == 1
    assert convs[0]["message_count"] == 1
    assert "hello there" in convs[0]["last_message"]


def test_get_conversation_messages(db_session):
    u = _user(db_session)
    conv = chat.get_or_create_conversation(u.id, None, db_session)
    db_session.add(Message(conversation_id=conv.id, role="user", content="q"))
    db_session.commit()
    msgs = chat.get_conversation_messages(conv.id, u.id, db_session)
    assert len(msgs) == 1 and msgs[0]["role"] == "user"


def test_get_conversation_messages_wrong_user_empty(db_session):
    u = _user(db_session)
    conv = chat.get_or_create_conversation(u.id, None, db_session)
    assert chat.get_conversation_messages(conv.id, "other", db_session) == []


def test_delete_conversation(db_session):
    u = _user(db_session)
    conv = chat.get_or_create_conversation(u.id, None, db_session)
    assert chat.delete_conversation(conv.id, u.id, db_session) is True
    assert chat.delete_conversation(conv.id, u.id, db_session) is False


def test_get_token_stats(db_session):
    u = _user(db_session)
    conv = chat.get_or_create_conversation(u.id, None, db_session)
    db_session.add(Message(conversation_id=conv.id, role="user", content="q", tokens_used=0))
    db_session.add(Message(conversation_id=conv.id, role="assistant", content="a", tokens_used=100))
    db_session.commit()
    stats = chat.get_token_stats(u.id, db_session)
    assert stats["total_tokens"] == 100
    assert stats["ai_messages"] == 1
    assert stats["avg_tokens_per_msg"] == 100.0
    assert stats["estimated_cost_usd"] == round(100 / 1000 * 0.005, 4)


# ── chat_stream ───────────────────────────────────────────────────
async def _collect(gen):
    return [chunk async for chunk in gen]


async def test_chat_stream_graceful_error_path(db_session):
    """With the default (non-awaitable) OpenAI stub, the stream degrades
    gracefully to an error message and still persists both messages."""
    u = _user(db_session)
    chunks = await _collect(chat.chat_stream(u.id, None, "why did prod break?", db_session))

    assert any("error" in c.lower() for c in chunks)
    assert any('"done": true' in c for c in chunks)

    saved = db_session.query(Message).all()
    roles = {m.role for m in saved}
    assert roles == {"user", "assistant"}


async def test_chat_stream_success_path(monkeypatch, db_session):
    u = _user(db_session)

    class _Delta:
        def __init__(self, c): self.content = c

    class _Choice:
        def __init__(self, c): self.delta = _Delta(c)

    class _Chunk:
        def __init__(self, c): self.choices = [_Choice(c)]

    async def _fake_create(**kwargs):
        async def _gen():
            for tok in ["Roll", " back", " to dep-0"]:
                yield _Chunk(tok)
        return _gen()

    fake_client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=_fake_create)))
    monkeypatch.setattr(chat, "_client", lambda: fake_client)

    chunks = await _collect(chat.chat_stream(u.id, None, "what should I do?", db_session))
    joined = "".join(chunks)
    assert "Roll" in joined and "dep-0" in joined

    assistant = db_session.query(Message).filter_by(role="assistant").first()
    assert assistant.content == "Roll back to dep-0"


async def test_chat_stream_sets_title_from_first_message(db_session):
    u = _user(db_session)
    await _collect(chat.chat_stream(u.id, None, "How do I roll back safely?", db_session))
    conv = db_session.query(Conversation).first()
    assert conv.title.startswith("How do I roll back")
