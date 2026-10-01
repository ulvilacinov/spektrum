from dataclasses import dataclass, field

from app.domain.enums import AIProviderKind


@dataclass(frozen=True, slots=True)
class AIConfig:
    """Which AI a user works with. Built from their saved settings (key decrypted)."""

    provider: AIProviderKind
    model: str
    api_key: str = field(repr=False)
    base_url: str | None = None
