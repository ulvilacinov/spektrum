from fastapi import status

from app.core.exceptions import AppError


class AIProviderError(AppError):
    """The AI service failed or could not be reached."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "ai_provider_error"


class AIResponseError(AIProviderError):
    """The AI answered, but not with valid structured output."""

    code = "ai_invalid_response"


class AINotConfiguredError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "ai_not_configured"


def provider_error(http_status: int | None, exc: Exception) -> AIProviderError:
    """Translate a vendor SDK failure into one error for every provider."""
    reason = {"reason": str(exc)[:500]}
    # Gemini answers an invalid key with 400 API_KEY_INVALID rather than 401.
    if http_status in (401, 403) or "API_KEY_INVALID" in str(exc):
        return AIProviderError(
            "The AI provider rejected the API key.", code="ai_invalid_key", details=reason
        )
    if http_status == 404:
        return AIProviderError(
            "The AI provider does not know this model.", code="ai_model_not_found", details=reason
        )
    if http_status == 429:
        return AIProviderError(
            "The AI service quota is exhausted. Try again later or raise the plan's limits.",
            code="ai_quota_exhausted",
            details=reason,
        )
    if http_status is not None and http_status >= 500:
        return AIProviderError(
            "The AI service is temporarily overloaded. Try again in a few minutes.",
            details=reason,
        )
    return AIProviderError("The AI service request failed.", details=reason)
