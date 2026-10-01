from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import SecretBox
from app.core.exceptions import UnprocessableError
from app.db.models import UserAISettings
from app.domain.entities import ChatMessage
from app.domain.enums import AIProviderKind, ChatRole
from app.services.ai import AIConfig, AINotConfiguredError, AIProvider

ProviderBuilder = Callable[[AIConfig], AIProvider]

TEST_PROMPT = "Antworte nur mit dem Wort: OK"


@dataclass(frozen=True, slots=True)
class AIDraft:
    """Values from the settings form. Without ``api_key`` the saved key is used, as long as
    it belongs to the same provider (and URL)."""

    provider: AIProviderKind
    model: str = ""
    base_url: str | None = None
    api_key: str | None = None


class AISettingsService:
    """Each user's choice of AI provider, model and API key (stored encrypted)."""

    def __init__(
        self, session: Session, *, secret_box: SecretBox, build_provider: ProviderBuilder
    ) -> None:
        self.session = session
        self.secret_box = secret_box
        self.build_provider = build_provider

    def get(self, user_id: int) -> UserAISettings | None:
        return self.session.scalar(select(UserAISettings).where(UserAISettings.user_id == user_id))

    def save(self, user_id: int, draft: AIDraft) -> UserAISettings:
        model = draft.model.strip()
        if not model:
            raise UnprocessableError("Choose a model.", code="ai_model_required")
        existing = self.get(user_id)
        api_key = self._resolve_key(existing, draft)
        base_url = self._valid_base_url(draft)
        settings = existing or UserAISettings(user_id=user_id)
        settings.provider = draft.provider
        settings.model = model
        settings.base_url = base_url
        settings.api_key_encrypted = self.secret_box.encrypt(api_key)
        settings.api_key_hint = api_key[-4:]
        if existing is None:
            self.session.add(settings)
        self.session.commit()
        self.session.refresh(settings)
        return settings

    def delete(self, user_id: int) -> None:
        existing = self.get(user_id)
        if existing is not None:
            self.session.delete(existing)
            self.session.commit()

    def provider_for(self, user_id: int) -> AIProvider:
        """The user's AI; ``ai_not_configured`` until they saved a provider and key."""
        settings = self.get(user_id)
        api_key = self.secret_box.decrypt(settings.api_key_encrypted) if settings else None
        if settings is None or api_key is None:
            raise AINotConfiguredError(
                "No AI provider is configured. Add your API key and model in the settings."
            )
        return self.build_provider(
            AIConfig(
                provider=settings.provider,
                model=settings.model,
                api_key=api_key,
                base_url=settings.base_url,
            )
        )

    def list_models(self, user_id: int, draft: AIDraft) -> list[str]:
        return self._draft_provider(user_id, draft).list_models()

    def test(self, user_id: int, draft: AIDraft) -> str:
        """One tiny chat request with the draft settings; returns the model's answer."""
        if not draft.model.strip():
            raise UnprocessableError("Choose a model.", code="ai_model_required")
        reply = self._draft_provider(user_id, draft).chat(
            [ChatMessage(role=ChatRole.USER, content=TEST_PROMPT)]
        )
        return reply[:200]

    def _draft_provider(self, user_id: int, draft: AIDraft) -> AIProvider:
        api_key = self._resolve_key(self.get(user_id), draft)
        return self.build_provider(
            AIConfig(
                provider=draft.provider,
                model=draft.model.strip(),
                api_key=api_key,
                base_url=self._valid_base_url(draft),
            )
        )

    def _resolve_key(self, existing: UserAISettings | None, draft: AIDraft) -> str:
        if draft.api_key and draft.api_key.strip():
            return draft.api_key.strip()
        same_target = (
            existing is not None
            and existing.provider == draft.provider
            and existing.base_url == self._valid_base_url(draft)
        )
        stored = self.secret_box.decrypt(existing.api_key_encrypted) if same_target else None
        if stored is None:
            raise UnprocessableError("Enter the API key.", code="ai_api_key_required")
        return stored

    @staticmethod
    def _valid_base_url(draft: AIDraft) -> str | None:
        if draft.provider is not AIProviderKind.OPENAI_COMPATIBLE:
            return None
        url = (draft.base_url or "").strip().rstrip("/")
        parsed = urlparse(url)
        # HTTPS only: the server must not be pointed at plain-HTTP or internal addresses.
        if parsed.scheme != "https" or not parsed.hostname:
            raise UnprocessableError(
                "Enter the service's base URL starting with https://.",
                code="ai_invalid_base_url",
            )
        return url
