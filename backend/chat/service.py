"""
Quorum -- AI Chat Service
General-purpose AI assistant with Cognee persistent memory.
Every conversation is stored so context accumulates across sessions.
"""

import json
import logging
from typing import AsyncGenerator

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

import cognee_service
from db_models import Conversation, Message
from config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()
_oai: AsyncOpenAI | None = None

_GROQ_BASE = "https://api.groq.com/openai/v1"
_SSE_SEP   = "\n\n"


def _client() -> AsyncOpenAI:
    global _oai
    if _oai is None:
        if settings.LLM_PROVIDER == "groq" and settings.GROQ_API_KEY:
            _oai = AsyncOpenAI(api_key=settings.GROQ_API_KEY, base_url=_GROQ_BASE)
        else:
            _oai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _oai


def _sse(payload: dict) -> str:
    return "data: " + json.dumps(payload) + _SSE_SEP


def get_or_create_conversation(user_id: str, conversation_id, db: Session):
    if conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        ).first()
        if conv:
            return conv
    conv = Conversation(user_id=user_id)
    db.add(conv); db.commit(); db.refresh(conv)
    return conv


def list_conversations(user_id: str, db: Session) -> list:
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
        .limit(30).all()
    )
    result = []
    for c in convs:
        last = c.messages[-1].content[:60] if c.messages else ""
        result.append({
            "id": c.id, "title": c.title, "last_message": last,
            "message_count": len(c.messages),
            "created_at": str(c.created_at),
            "updated_at": str(c.updated_at) if c.updated_at else str(c.created_at),
        })
    return result


def get_conversation_messages(conversation_id: str, user_id: str, db: Session) -> list:
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
    ).first()
    if not conv:
        return []
    return [
        {"id": m.id, "role": m.role, "content": m.content,
         "tokens_used": m.tokens_used, "created_at": str(m.created_at)}
        for m in conv.messages
    ]


def delete_conversation(conversation_id: str, user_id: str, db: Session) -> bool:
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
    ).first()
    if not conv:
        return False
    db.delete(conv); db.commit()
    return True


async def chat_stream(user_id, conversation_id, user_message, db) -> AsyncGenerator[str, None]:
    """Stream an AI response with persistent Cognee memory. Yields SSE frames."""

    conv = get_or_create_conversation(user_id, conversation_id, db)

    user_msg = Message(conversation_id=conv.id, role="user", content=user_message)
    db.add(user_msg); db.commit()

    # Recall relevant memory from Cognee graph
    memory_context = {"answer": "", "insights": [], "summaries": []}
    try:
        memory_context = await cognee_service.recall(
            cpu=0.0, error_rate=0.0, latency=0.0, anomaly_desc=user_message,
        )
    except Exception as e:
        logger.warning("Cognee recall skipped: %s", e)

    memory_text  = (memory_context.get("answer") or "").strip()
    insights     = memory_context.get("insights") or []

    insight_lines = [
        "  - " + str(i.get("subject","?")) + " -> " + str(i.get("relationship","?")) + " -> " + str(i.get("object","?"))
        for i in insights[:4] if i.get("subject") or i.get("object")
    ]

    # In-session conversation history (last 14 turns)
    history = [
        {"role": m.role, "content": m.content}
        for m in conv.messages[-14:]
        if m.id != user_msg.id
    ]

    # Build memory block
    memory_parts = []
    if memory_text:
        memory_parts.append("What Quorum remembers relevant to this:\n" + memory_text)
    if insight_lines:
        memory_parts.append("Graph connections:\n" + "\n".join(insight_lines))

    deployments = cognee_service.get_all_deployments()
    keywords = user_message.lower().split()
    relevant_deps = [
        d for d in deployments
        if any(kw in (d.id + d.author + d.commit_message + " ".join(d.services_affected)).lower()
               for kw in keywords if len(kw) > 3)
    ]
    if relevant_deps:
        dep_lines = "\n".join(
            "  - [" + d.status + "] " + d.id + ": " + d.commit_message[:80]
            for d in relevant_deps[:4]
        )
        memory_parts.append("Relevant deployments:\n" + dep_lines)

    memory_block = "\n\n".join(memory_parts) if memory_parts else "(no prior memory relevant to this message)"

    system_prompt = (
        "You are a helpful, knowledgeable AI assistant built into Quorum, a production reliability platform. "
        "You have two defining qualities:\n\n"
        "GENERAL INTELLIGENCE: Answer any question on any topic -- coding, writing, math, analysis, "
        "advice, creative work, explanations. You are as capable and conversational as the best AI assistants. "
        "Never say you cannot help or that you lack knowledge -- engage with everything.\n\n"
        "PERSISTENT MEMORY: Quorum stores all conversations and system events in Cognee's knowledge graph. "
        "You can recall what was discussed in previous sessions. When memory surfaces something relevant, "
        "weave it in naturally: 'Based on what we discussed before...', 'I remember you mentioned...', "
        "'According to your deployment history...'. Only reference memory when it genuinely helps -- "
        "don't force it.\n\n"
        "=== MEMORY FOR THIS MESSAGE ===\n" + memory_block + "\n\n"
        "=== STYLE ===\n"
        "Conversational for casual questions, precise and structured for technical ones. "
        "Use markdown and code blocks when they improve clarity. "
        "Be thorough but never pad. Match length to complexity. "
        "Never start with 'As an AI' or similar hedges -- just answer."
    )

    full_response = ""
    tokens_used   = 0

    try:
        stream = await _client().chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                *history,
                {"role": "user", "content": user_message},
            ],
            stream=True, max_tokens=2048, temperature=0.7,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                full_response += delta
                yield _sse({"text": delta, "conversation_id": conv.id})
        tokens_used = len(full_response.split()) * 2

    except Exception as e:
        logger.error("LLM error: %s", e)
        msg = "LLM error: " + str(e) + ". Check GROQ_API_KEY in backend/.env."
        full_response = msg
        yield _sse({"text": msg, "conversation_id": conv.id})

    ai_msg = Message(conversation_id=conv.id, role="assistant",
                     content=full_response, tokens_used=tokens_used)
    db.add(ai_msg)

    if conv.title == "New conversation" and len(conv.messages) <= 2:
        conv.title = user_message[:50] + ("..." if len(user_message) > 50 else "")

    db.commit()

    # Ingest into Cognee so future sessions can recall this conversation
    try:
        import cognee
        mem = "USER SAID: " + user_message + "\nASSISTANT REPLIED: " + full_response[:1000]
        await cognee.add(mem, dataset_name="quorum_chat_" + user_id[:8])
        await cognee.cognify()
    except Exception as e:
        logger.debug("Memory ingestion skipped: %s", e)

    yield _sse({"done": True, "conversation_id": conv.id, "tokens": tokens_used})


def get_token_stats(user_id: str, db: Session) -> dict:
    messages = (
        db.query(Message)
        .join(Conversation)
        .filter(Conversation.user_id == user_id)
        .all()
    )
    total_tokens = sum(m.tokens_used for m in messages)
    ai_messages  = [m for m in messages if m.role == "assistant"]
    return {
        "total_tokens":        total_tokens,
        "total_messages":      len(messages),
        "ai_messages":         len(ai_messages),
        "avg_tokens_per_msg":  round(total_tokens / max(len(ai_messages), 1), 1),
        "estimated_cost_usd":  round(total_tokens / 1000 * 0.005, 4),
    }
