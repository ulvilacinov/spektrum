from pydantic import BaseModel, Field, field_validator

from app.domain.entities import ChatMessage
from app.domain.enums import ChatRole

MAX_MESSAGE_LENGTH = 8000


class ChatMessageIn(BaseModel):
    role: ChatRole
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)

    @field_validator("content")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("The message must not be empty.")
        return value

    def to_entity(self) -> ChatMessage:
        return ChatMessage(role=self.role, content=self.content)


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn] = Field(
        min_length=1,
        max_length=100,
        description="The conversation, oldest first; the last message is the new question. "
        "Only the most recent messages are sent to the AI.",
    )


class ChatReply(BaseModel):
    reply: str = Field(description="The tutor's answer in Turkish (simple Markdown).")
