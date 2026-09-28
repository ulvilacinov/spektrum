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
