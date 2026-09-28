from functools import lru_cache

from app.core.config import Settings
from app.services.ai.errors import AINotConfiguredError
from app.services.ai.gemini import GeminiAIProvider
from app.services.ai.provider import AIProvider
from app.services.ai.rate_limit import RateLimiter


def create_ai_provider(settings: Settings) -> AIProvider:
    """Build the configured provider. The only place that knows concrete implementations."""
    if settings.ai_provider == "gemini":
        api_key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else ""
        if not api_key.strip():
            raise AINotConfiguredError("GEMINI_API_KEY is not set; document analysis needs it.")
        return GeminiAIProvider(
            api_key=api_key.strip(),
            model=settings.gemini_model,
            timeout_seconds=settings.ai_request_timeout_seconds,
            rate_limiter=_shared_rate_limiter(
                f"gemini:{settings.gemini_model}", settings.ai_requests_per_minute
            ),
        )
    raise AINotConfiguredError(f"Unknown AI provider: {settings.ai_provider!r}")


@lru_cache
def _shared_rate_limiter(key: str, requests_per_minute: int | None) -> RateLimiter | None:
    """One limiter per provider/model for the whole process (quotas are per model)."""
    return RateLimiter(requests_per_minute) if requests_per_minute else None
