"""
Quorum — AI Chat Service
Cognee-powered conversational memory. Every message is ingested into
Cognee so context accumulates across sessions and references live
deployment/incident knowledge.
"""

import json
import logging
from typing import AsyncGenerator

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

import cognee_service
from db_models import Conversation, Message
from config import get_settings

logger  = logging.getLogger(__name__)
settings = get_settings()
_oai: AsyncOpenAI | None = None


def _client() -> AsyncOpenAI:
    global _oai
    if _oai is None:
        _oai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _oai


# ── Conversation management ───────────────────────────────────

def get_or_create_conversation(user_id: str, conversation_id: str | None, db: Session) -> Conversation:
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


def list_conversations(user_id: str, db: Session) -> list[dict]:
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
        .limit(30)
        .all()
    )
    result = []
    for c in convs:
        last = c.messages[-1].content[:60] if c.messages else ""
        result.append({
            "id": c.id, "title": c.title,
            "last_message": last,
            "message_count": len(c.messages),
            "created_at": str(c.created_at),
            "updated_at": str(c.updated_at) if c.updated_at else str(c.created_at),
        })
    return result


def get_conversation_messages(conversation_id: str, user_id: str, db: Session) -> list[dict]:
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


# ── Streaming chat ────────────────────────────────────────────

async def chat_stream(
    user_id: str,
    conversation_id: str,
    user_message: str,
    db: Session,
) -> AsyncGenerator[str, None]:
    """Stream an AI response with Cognee memory context. Yields SSE data lines."""

    conv = get_or_create_conversation(user_id, conversation_id, db)

    # 1. Save user message
    user_msg = Message(conversation_id=conv.id, role="user", content=user_message)
    db.add(user_msg); db.commit()

    # 2. Recall Cognee memory — deployment/incident graph + conversation history
    memory_context: dict = {"answer": "", "insights": []}
    try:
        memory_context = await cognee_service.recall(
            cpu=0.0, error_rate=0.0, latency=0.0,
            anomaly_desc=user_message,
        )
    except Exception as e:
        logger.warning(f"Cognee recall failed in chat: {e}")

    memory_text = memory_context.get("answer", "")
    insights    = memory_context.get("insights", [])
    insight_str = "\n".join(
        f"  {i.get('subject')} → {i.get('relationship')} → {i.get('object')}"
        for i in insights[:5]
    ) if insights else "  None yet"

    # 3. Build conversation history (last 12 messages for context window)
    history = [
        {"role": m.role, "content": m.content}
        for m in conv.messages[-12:]
        if m.id != user_msg.id
    ]

    deployments = cognee_service.get_all_deployments()
    dep_summary = "\n".join(
        f"  {d.id}: {d.commit_sha[:8]} — {d.commit_message[:60]} [{d.status}]"
        for d in deployments[-6:]
    ) if deployments else "  None ingested yet"

    system_prompt = f"""You are Quorum AI — an expert production incident prevention assistant with deep memory of this system's deployment history, past incidents, and operational patterns.

Your knowledge comes from Cognee's hybrid graph-vector memory, which stores causal chains between deployments, incidents, root causes, and safe states.

=== CURRENT COGNEE MEMORY RECALL ===
{memory_text or "No matching memory found yet. Answer based on general expertise."}

=== GRAPH INSIGHTS (entity relationships) ===
{insight_str}

=== RECENT DEPLOYMENTS IN MEMORY ===
{dep_summary}

=== YOUR CAPABILITIES ===
- Recall which deployments caused past incidents and why
- Identify the safe rollback state for any scenario
- Analyze patterns across multiple incidents
- Explain root causes with causal chain reasoning
- Answer natural language questions about system history

=== INSTRUCTIONS ===
- Be specific: cite deployment IDs (dep-XXX), commit SHAs, and incident IDs when relevant
- Explain your reasoning based on graph relationships, not guesses
- If memory is sparse, say so and suggest seeding more incident data
- Keep responses concise and actionable for on-call engineers
- Format structured data (deployment lists, comparisons) in markdown tables"""

    # 4. Stream from OpenAI
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
            stream=True,
            max_tokens=1500,
            temperature=0.3,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                full_response += delta
                yield f"data: {json.dumps({'text': delta, 'conversation_id': conv.id})}\n\n"

        tokens_used = len(full_response.split()) * 2  # rough estimate

    except Exception as e:
        error_msg = f"I encountered an error: {e}. Please check that OPENAI_API_KEY is set in your .env."
        full_response = error_msg
        yield f"data: {json.dumps({'text': error_msg, 'conversation_id': conv.id})}\n\n"

    # 5. Save assistant response
    ai_msg = Message(
        conversation_id=conv.id, role="assistant",
        content=full_response, tokens_used=tokens_used,
    )
    db.add(ai_msg)

    # 6. Update conversation title from first message
    if conv.title == "New conversation" and len(conv.messages) <= 2:
        conv.title = user_message[:50] + ("…" if len(user_message) > 50 else "")

    db.commit()

    # 7. Ingest conversation into Cognee memory (non-blocking)
    try:
        import cognee
        mem = f"QUORUM CHAT LOG\nUser: {user_message}\nQuorum AI: {full_response[:500]}"
        await cognee.add(mem, dataset_name=f"quorum_chat_{user_id[:8]}")
        await cognee.cognify()
    except Exception as e:
        logger.debug(f"Chat memory ingestion skipped: {e}")

    yield f"data: {json.dumps({'done': True, 'conversation_id': conv.id, 'tokens': tokens_used})}\n\n"


# ── Token usage stats ─────────────────────────────────────────
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
