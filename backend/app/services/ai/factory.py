from functools import lru_cache

from app.core.config import Settings
from app.domain.enums import AIProviderKind
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.config import AIConfig
from app.services.ai.gemini import GeminiAIProvider
from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.provider import AIProvider
from app.services.ai.rate_limit import RateLimiter


def create_ai_provider(config: AIConfig, settings: Settings) -> AIProvider:
    """Build a provider. The only place that knows the concrete implementations."""
    timeout = settings.ai_request_timeout_seconds
    match config.provider:
        case AIProviderKind.GEMINI:
            return GeminiAIProvider(
                api_key=config.api_key,
                model=config.model,
                timeout_seconds=timeout,
                rate_limiter=_shared_rate_limiter(
                    f"gemini:{config.model}", settings.ai_requests_per_minute
                ),
            )
        case AIProviderKind.OPENAI:
            return OpenAIProvider(
                api_key=config.api_key, model=config.model, timeout_seconds=timeout
            )
        case AIProviderKind.OPENAI_COMPATIBLE:
            return OpenAIProvider(
                api_key=config.api_key,
                model=config.model,
                timeout_seconds=timeout,
                base_url=config.base_url,
                json_schema=False,
            )
        case AIProviderKind.ANTHROPIC:
            return AnthropicProvider(
                api_key=config.api_key,
                model=config.model,
                timeout_seconds=timeout,
                max_output_tokens=settings.ai_max_output_tokens,
            )
    raise ValueError(f"Unknown AI provider: {config.provider!r}")


@lru_cache
def _shared_rate_limiter(key: str, requests_per_minute: int | None) -> RateLimiter | None:
    """One limiter per model for the whole process (Gemini's free quota is per model)."""
    return RateLimiter(requests_per_minute) if requests_per_minute else None
