from fastapi import APIRouter

from app.api.dependencies import ChatServiceDep
from app.schemas.chat import ChatReply, ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatReply)
def chat(payload: ChatRequest, service: ChatServiceDep) -> ChatReply:
    """Ask the AI tutor a quick question. Nothing is stored; send the recent history."""
    reply = service.reply([message.to_entity() for message in payload.messages])
    return ChatReply(reply=reply)
