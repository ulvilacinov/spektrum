from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field

from app.db.models import UserAISettings
from app.domain.enums import AIProviderKind
from app.services.ai_settings import AIDraft


class AISettingsRead(BaseModel):
    configured: bool
    provider: AIProviderKind | None = None
    model: str | None = None
    base_url: str | None = None
    api_key_hint: str | None = Field(
        default=None, description="Last characters of the saved key; the key is never returned."
    )
    updated_at: datetime | None = None

    @classmethod
    def from_settings(cls, settings: UserAISettings | None) -> Self:
        if settings is None:
            return cls(configured=False)
        return cls(
            configured=True,
            provider=settings.provider,
            model=settings.model,
            base_url=settings.base_url,
            api_key_hint=settings.api_key_hint,
            updated_at=settings.updated_at,
        )


class AIDraftIn(BaseModel):
    provider: AIProviderKind
    model: str = Field(default="", max_length=200)
    base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(
        default=None,
        max_length=500,
        description="Leave empty to keep the saved key (same provider and URL).",
    )

    def to_draft(self) -> AIDraft:
        return AIDraft(
            provider=self.provider, model=self.model, base_url=self.base_url, api_key=self.api_key
        )


class AIModelsRead(BaseModel):
    models: list[str]


class AITestRead(BaseModel):
    reply: str
