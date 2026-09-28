import logging
import re
import time
from collections.abc import Callable, Sequence
from typing import Any

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

from app.domain.entities import ExtractedPage
from app.services.ai import prompts
from app.services.ai.errors import AIProviderError, AIResponseError
from app.services.ai.provider import AIProvider
from app.services.ai.rate_limit import RateLimiter
from app.services.ai.schemas import (
    AnswerEvaluationRequest,
    AnswerEvaluationResult,
    ChapterDetectionResult,
    VocabularyExtractionResult,
)

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


class GeminiAIProvider(AIProvider):
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
        self.model = model
        # Extra attempts only for answers that are not valid structured output.
        self.max_attempts = max_attempts
        self.rate_limiter = rate_limiter
        self._sleep = sleep
        self.client = client or genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=timeout_seconds * 1000, retry_options=_RETRY_OPTIONS
            ),
        )

    def extract_chapters(self, pages: Sequence[ExtractedPage]) -> ChapterDetectionResult:
        return self._generate(
            system=prompts.CHAPTER_DETECTION_SYSTEM,
            prompt=prompts.chapter_detection_prompt(pages),
            schema=ChapterDetectionResult,
        )

    def extract_vocabulary(
        self,
        chapter_title: str,
        pages: Sequence[ExtractedPage],
        next_chapter_title: str | None = None,
    ) -> VocabularyExtractionResult:
        return self._generate(
            system=prompts.VOCABULARY_EXTRACTION_SYSTEM,
            prompt=prompts.vocabulary_extraction_prompt(chapter_title, pages, next_chapter_title),
            schema=VocabularyExtractionResult,
        )

    def evaluate_answer(self, request: AnswerEvaluationRequest) -> AnswerEvaluationResult:
        return self._generate(
            system=prompts.ANSWER_EVALUATION_SYSTEM,
            prompt=prompts.answer_evaluation_prompt(request),
            schema=AnswerEvaluationResult,
        )

    def _generate[T: BaseModel](self, *, system: str, prompt: str, schema: type[T]) -> T:
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        problem = "no attempt made"
        for attempt in range(1, self.max_attempts + 1):
            response = self._request(prompt, config)
            if _finish_reason(response) == types.FinishReason.MAX_TOKENS:
                raise AIResponseError(
                    "The AI response was cut off because it was too long. "
                    "Lower AI_MAX_PAGES_PER_REQUEST and analyze again."
                )
            text = response.text
            if not text:
                problem = f"empty response (finish reason: {_finish_reason(response)})"
            else:
                try:
                    return schema.model_validate_json(text)
                except ValidationError as exc:
                    problem = f"invalid structured output: {exc.errors()[:3]}"
            logger.warning(
                "Gemini attempt %d/%d for %s failed: %s",
                attempt,
                self.max_attempts,
                schema.__name__,
                problem,
            )
        raise AIResponseError(
            "The AI service did not return valid structured output.",
            details={"reason": problem[:500]},
        )

    def _request(self, prompt: str, config: types.GenerateContentConfig) -> Any:
        """One generate_content call; waits out per-minute rate limits (HTTP 429)."""
        waits = 0
        while True:
            if self.rate_limiter:
                self.rate_limiter.acquire()
            try:
                return self.client.models.generate_content(
                    model=self.model, contents=prompt, config=config
                )
            except errors.APIError as exc:
                delay = _rate_limit_delay(exc)
                if delay is None or delay > MAX_RATE_LIMIT_DELAY or waits >= MAX_RATE_LIMIT_WAITS:
                    raise _provider_error(exc) from exc
                waits += 1
                logger.warning("Gemini rate limit hit; retrying in %.0fs", delay)
                self._sleep(delay)
            except Exception as exc:  # transport errors, timeouts
                raise _provider_error(exc) from exc


def _rate_limit_delay(exc: errors.APIError) -> float | None:
    """Seconds the API asks us to wait for a 429, or None for any other error."""
    if exc.code != 429:
        return None
    match = _RETRY_DELAY.search(str(exc))
    if not match:
        return DEFAULT_RATE_LIMIT_DELAY
    return float(match.group(1) or match.group(2)) + 1.0


def _provider_error(exc: Exception) -> AIProviderError:
    code = exc.code if isinstance(exc, errors.APIError) else None
    if code == 429:
        message = "The AI service quota is exhausted. Try again later or raise the plan's limits."
    elif code is not None and code >= 500:
        message = "The AI service is temporarily overloaded. Try again in a few minutes."
    else:
        message = "The AI service request failed."
    return AIProviderError(message, details={"reason": str(exc)[:500]})


def _finish_reason(response: Any) -> Any:
    candidates = getattr(response, "candidates", None) or []
    return getattr(candidates[0], "finish_reason", None) if candidates else None
