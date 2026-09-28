import json
from types import SimpleNamespace
from typing import Any

import pytest
from google.genai import errors, types

from app.core.config import Settings
from app.domain.entities import ExtractedPage
from app.services.ai import (
    AINotConfiguredError,
    AIProviderError,
    AIResponseError,
    create_ai_provider,
)
from app.services.ai.gemini import GeminiAIProvider
from app.services.ai.schemas import ChapterDetectionResult, VocabularyExtractionResult

PAGES = [
    ExtractedPage(page_number=2, text="Kapitel 1\ndie Veranstaltung"),
    ExtractedPage(page_number=3, text="im Stau stehen"),
]


def response(text: str | None, finish_reason: Any = types.FinishReason.STOP) -> SimpleNamespace:
    return SimpleNamespace(text=text, candidates=[SimpleNamespace(finish_reason=finish_reason)])


class FakeModels:
    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def provider(*outcomes: Any) -> tuple[GeminiAIProvider, FakeModels]:
    models = FakeModels(*outcomes)
    gemini = GeminiAIProvider(
        api_key="test",
        model="gemini-test",
        timeout_seconds=10,
        client=SimpleNamespace(models=models),
    )
    return gemini, models


def test_extract_chapters_sends_page_markers_and_structured_schema() -> None:
    payload = {"chapters": [{"title": "Kapitel 1", "chapter_number": 1, "start_page": 2}]}
    gemini, models = provider(response(json.dumps(payload)))

    result = gemini.extract_chapters(PAGES)

    assert result.chapters[0].title == "Kapitel 1"
    call = models.calls[0]
    assert call["model"] == "gemini-test"
    assert "=== PAGE 2 ===\nKapitel 1\ndie Veranstaltung" in call["contents"]
    assert "=== PAGE 3 ===" in call["contents"]
    assert call["config"].response_mime_type == "application/json"
    assert call["config"].response_schema is ChapterDetectionResult


def test_extract_vocabulary_parses_sections() -> None:
    payload = {
        "chapter_title": "Kapitel 1",
        "sections": [
            {
                "name": "Alltag",
                "items": [
                    {
                        "german": "im Stau stehen",
                        "turkish": "trafikte kalmak",
                        "item_type": "phrase",
                        "base_verb": "stehen",
                        "source_text": "im Stau stehen",
                        "source_page": 3,
                    }
                ],
            }
        ],
    }
    gemini, models = provider(response(json.dumps(payload)))

    result = gemini.extract_vocabulary("Kapitel 1", PAGES, next_chapter_title="Kapitel 2")

    assert isinstance(result, VocabularyExtractionResult)
    assert [(i.german, i.item_type, i.source_page) for i in result.items] == [
        ("im Stau stehen", "phrase", 3)
    ]
    assert "'Kapitel 2'" in models.calls[0]["contents"]
    assert models.calls[0]["config"].response_schema is VocabularyExtractionResult


def test_retries_once_on_invalid_structured_output() -> None:
    gemini, models = provider(response("not json"), response('{"chapters": []}'))

    assert gemini.extract_chapters(PAGES).chapters == []
    assert len(models.calls) == 2


def test_gives_up_after_repeated_invalid_output() -> None:
    gemini, _ = provider(response(None), response('{"chapters": "nope"}'))

    with pytest.raises(AIResponseError) as exc_info:
        gemini.extract_chapters(PAGES)
    assert exc_info.value.status_code == 502


def test_truncated_response_is_reported_without_retry() -> None:
    gemini, models = provider(response('{"chap', finish_reason=types.FinishReason.MAX_TOKENS))

    with pytest.raises(AIResponseError, match="AI_MAX_PAGES_PER_REQUEST"):
        gemini.extract_chapters(PAGES)
    assert len(models.calls) == 1


def test_sdk_errors_become_provider_errors() -> None:
    gemini, _ = provider(RuntimeError("quota exceeded"))

    with pytest.raises(AIProviderError) as exc_info:
        gemini.extract_chapters(PAGES)
    assert exc_info.value.code == "ai_provider_error"
    assert exc_info.value.details == {"reason": "quota exceeded"}


@pytest.mark.parametrize("api_key", [None, "", "   "])
def test_factory_requires_an_api_key(api_key: str | None) -> None:
    settings = Settings(_env_file=None, gemini_api_key=api_key)

    with pytest.raises(AINotConfiguredError):
        create_ai_provider(settings)


def test_factory_builds_gemini_provider() -> None:
    settings = Settings(_env_file=None, gemini_api_key="key", gemini_model="gemini-x")

    ai = create_ai_provider(settings)

    assert isinstance(ai, GeminiAIProvider)
    assert ai.model == "gemini-x"


def api_error(code: int, message: str) -> errors.APIError:
    status = "RESOURCE_EXHAUSTED" if code == 429 else "INVALID_ARGUMENT"
    return errors.ClientError(code, {"error": {"code": code, "message": message, "status": status}})


def limited_provider(*outcomes: Any) -> tuple[GeminiAIProvider, FakeModels, list[float]]:
    models = FakeModels(*outcomes)
    sleeps: list[float] = []
    gemini = GeminiAIProvider(
        api_key="test",
        model="gemini-test",
        timeout_seconds=10,
        client=SimpleNamespace(models=models),
        sleep=sleeps.append,
    )
    return gemini, models, sleeps


def test_rate_limit_waits_the_suggested_delay_and_retries() -> None:
    gemini, models, sleeps = limited_provider(
        api_error(429, "Quota exceeded. Please retry in 12.5s."), response('{"chapters": []}')
    )

    assert gemini.extract_chapters(PAGES).chapters == []
    assert sleeps == [13.5]
    assert len(models.calls) == 2


def test_exhausted_daily_quota_fails_without_waiting() -> None:
    gemini, models, sleeps = limited_provider(api_error(429, "Please retry in 3600s."))

    with pytest.raises(AIProviderError, match="quota is exhausted"):
        gemini.extract_chapters(PAGES)
    assert sleeps == []
    assert len(models.calls) == 1


def test_gives_up_after_repeated_rate_limits() -> None:
    gemini, models, sleeps = limited_provider(
        *[api_error(429, "Please retry in 1s.") for _ in range(4)]
    )

    with pytest.raises(AIProviderError, match="quota is exhausted"):
        gemini.extract_chapters(PAGES)
    assert len(sleeps) == 3
    assert len(models.calls) == 4


def test_other_api_errors_are_not_retried() -> None:
    gemini, models, sleeps = limited_provider(api_error(400, "Invalid schema."))

    with pytest.raises(AIProviderError, match="request failed"):
        gemini.extract_chapters(PAGES)
    assert sleeps == [] and len(models.calls) == 1


def test_every_request_passes_the_rate_limiter() -> None:
    acquired: list[int] = []
    models = FakeModels(response("not json"), response('{"chapters": []}'))
    gemini = GeminiAIProvider(
        api_key="test",
        model="gemini-test",
        timeout_seconds=10,
        client=SimpleNamespace(models=models),
        rate_limiter=SimpleNamespace(acquire=lambda: acquired.append(1)),
    )

    gemini.extract_chapters(PAGES)

    assert len(acquired) == 2


def test_factory_shares_one_rate_limiter_per_model() -> None:
    settings = Settings(_env_file=None, gemini_api_key="key", ai_requests_per_minute=5)

    first, second = create_ai_provider(settings), create_ai_provider(settings)

    assert first.rate_limiter is not None
    assert first.rate_limiter is second.rate_limiter
    unlimited = Settings(_env_file=None, gemini_api_key="key", ai_requests_per_minute=None)
    assert create_ai_provider(unlimited).rate_limiter is None


def test_server_overload_has_a_helpful_message() -> None:
    overloaded = errors.ServerError(
        503, {"error": {"code": 503, "message": "high demand", "status": "UNAVAILABLE"}}
    )
    gemini, _, _ = limited_provider(overloaded)

    with pytest.raises(AIProviderError, match="temporarily overloaded"):
        gemini.extract_chapters(PAGES)
