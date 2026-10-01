import logging
import re
import time
from collections.abc import Callable, Sequence
from typing import Any

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.domain.entities import ChatMessage
from app.domain.enums import ChatRole
from app.services.ai import prompts
from app.services.ai.base import StructuredAIProvider, truncated_error
from app.services.ai.errors import AIResponseError, provider_error
from app.services.ai.rate_limit import RateLimiter

logger = logging.getLogger(__name__)

# Transient server failures are retried by the SDK with exponential backoff. 429 is handled
# below instead: quick SDK retries would only burn more of the quota.
_RETRY_OPTIONS = types.HttpRetryOptions(
    attempts=5, initial_delay=2.0, max_delay=30.0, http_status_codes=[408, 500, 502, 503, 504]
)
_RETRY_DELAY = re.compile(r"retry in ([\d.]+)s|'retryDelay': '([\d.]+)s'", re.IGNORECASE)
DEFAULT_RATE_LIMIT_DELAY = 30.0
# A longer suggested wait means a daily quota is exhausted; waiting would not help.
MAX_RATE_LIMIT_DELAY = 90.0
MAX_RATE_LIMIT_WAITS = 3


class GeminiAIProvider(StructuredAIProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int,
        max_attempts: int = 2,
        rate_limiter: RateLimiter | None = None,
        client: Any | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        super().__init__(max_attempts=max_attempts)
        self.model = model
        self.rate_limiter = rate_limiter
        self._sleep = sleep
        self.client = client or genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=timeout_seconds * 1000, retry_options=_RETRY_OPTIONS
            ),
        )

    def _generate_structured(
        self, *, system: str, prompt: str, schema: type[BaseModel]
    ) -> str | None:
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        response = self._request(prompt, config)
        if _finish_reason(response) == types.FinishReason.MAX_TOKENS:
            raise truncated_error()
        return response.text

    def chat(self, messages: Sequence[ChatMessage]) -> str:
        contents = [
            types.Content(
                role="user" if message.role == ChatRole.USER else "model",
                parts=[types.Part.from_text(text=message.content)],
            )
            for message in messages
        ]
        config = types.GenerateContentConfig(
            system_instruction=prompts.CHAT_SYSTEM,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        response = self._request(contents, config)
        text = (response.text or "").strip()
        if not text:
            raise AIResponseError(
                "The AI service returned an empty answer.",
                details={"reason": f"finish reason: {_finish_reason(response)}"},
            )
        return text

    def list_models(self) -> list[str]:
        try:
            models = list(self.client.models.list())
        except errors.APIError as exc:
            raise provider_error(exc.code, exc) from exc
        except Exception as exc:
            raise provider_error(None, exc) from exc
        names = [
            (model.name or "").removeprefix("models/")
            for model in models
            if "generateContent" in (model.supported_actions or [])
        ]
        return sorted(name for name in names if name)

    def _request(self, contents: Any, config: types.GenerateContentConfig) -> Any:
        """One generate_content call; waits out per-minute rate limits (HTTP 429)."""
        waits = 0
        while True:
            if self.rate_limiter:
                self.rate_limiter.acquire()
            try:
                return self.client.models.generate_content(
                    model=self.model, contents=contents, config=config
                )
            except errors.APIError as exc:
                delay = _rate_limit_delay(exc)
                if delay is None or delay > MAX_RATE_LIMIT_DELAY or waits >= MAX_RATE_LIMIT_WAITS:
                    raise provider_error(exc.code, exc) from exc
                waits += 1
                logger.warning("Gemini rate limit hit; retrying in %.0fs", delay)
                self._sleep(delay)
            except Exception as exc:  # transport errors, timeouts
                raise provider_error(None, exc) from exc


def _rate_limit_delay(exc: errors.APIError) -> float | None:
    """Seconds the API asks us to wait for a 429, or None for any other error."""
    if exc.code != 429:
        return None
    match = _RETRY_DELAY.search(str(exc))
    if not match:
        return DEFAULT_RATE_LIMIT_DELAY
    return float(match.group(1) or match.group(2)) + 1.0


def _finish_reason(response: Any) -> Any:
    candidates = getattr(response, "candidates", None) or []
    return getattr(candidates[0], "finish_reason", None) if candidates else None
