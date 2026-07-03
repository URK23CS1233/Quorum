"""Quorum — Chat Router (SSE streaming)"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from database import get_db
from dependencies import require_analyst, get_current_user
from db_models import User
from chat.service import (
    chat_stream, list_conversations, get_conversation_messages,
    delete_conversation, get_token_stats,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


@router.post("/message")
async def send_message(
    body: ChatRequest,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    """Stream an AI response. Returns Server-Sent Events."""
    return StreamingResponse(
        chat_stream(current_user.id, body.conversation_id, body.message, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations", response_model=List[dict])
async def get_conversations(
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    return list_conversations(current_user.id, db)


@router.get("/conversations/{conversation_id}/messages", response_model=List[dict])
async def get_messages(
    conversation_id: str,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    return get_conversation_messages(conversation_id, current_user.id, db)


@router.delete("/conversations/{conversation_id}")
async def remove_conversation(
    conversation_id: str,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    ok = delete_conversation(conversation_id, current_user.id, db)
    if not ok:
        raise HTTPException(404, "Conversation not found")
    return {"status": "ok"}


@router.get("/usage")
async def token_usage(
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    return get_token_stats(current_user.id, db)
