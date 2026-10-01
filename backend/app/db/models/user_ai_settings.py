from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, enum_column
from app.domain.enums import AIProviderKind


class UserAISettings(Base):
    """The AI provider, model and (encrypted) API key a user chose on the settings page."""

    __tablename__ = "user_ai_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    provider: Mapped[AIProviderKind] = mapped_column(
        enum_column(AIProviderKind, length=32), nullable=False
    )
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    # Only for OpenAI-compatible services.
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    # Shown on the settings page so the user recognises the key; the key itself never is.
    api_key_hint: Mapped[str] = mapped_column(String(8), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
