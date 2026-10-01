"""OpenAI, OpenAI-compatible and Anthropic providers with fake SDK clients."""

import json
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx
import openai
import pytest

from app.core.config import Settings
from app.domain.entities import ChatMessage, ExtractedPage
from app.domain.enums import AIProviderKind, ChatRole
from app.services.ai import AIConfig, AIProviderError, AIResponseError, create_ai_provider, prompts
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.schemas import ChapterDetectionResult

PAGES = [ExtractedPage(page_number=2, text="Kapitel 1\ndie Veranstaltung")]
CHAPTERS = {"chapters": [{"title": "Kapitel 1", "chapter_number": 1, "start_page": 2}]}
HISTORY = [
    ChatMessage(ChatRole.USER, "Merhaba"),
    ChatMessage(ChatRole.ASSISTANT, "Merhaba!"),
    ChatMessage(ChatRole.USER, "Tisch?"),
]


class Recorder:
    """Stands in for an SDK method: records the call, returns (or raises) the next outcome."""

    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


# ---------------------------------------------------------------- OpenAI


def completion(content: str | None, finish_reason: str = "stop") -> SimpleNamespace:
    message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=finish_reason)])


def openai_provider(*outcomes: Any, **options: Any) -> tuple[OpenAIProvider, Recorder]:
    create = Recorder(*outcomes)
    ids = options.pop("ids", [])
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
        models=SimpleNamespace(list=lambda: [SimpleNamespace(id=i) for i in ids]),
    )
    provider = OpenAIProvider(
        api_key="k", model="gpt-test", timeout_seconds=5, client=client, **options
    )
    return provider, create


def openai_status_error(status: int) -> openai.APIStatusError:
    response = httpx.Response(status, request=httpx.Request("POST", "https://api.openai.com"))
    return openai.APIStatusError("error", response=response, body=None)


def test_openai_asks_for_the_json_schema() -> None:
    provider, create = openai_provider(completion(json.dumps(CHAPTERS)))

    result = provider.extract_chapters(PAGES)

    assert result.chapters[0].title == "Kapitel 1"
    call = create.calls[0]
    assert call["model"] == "gpt-test"
    assert call["messages"][0] == {"role": "system", "content": prompts.CHAPTER_DETECTION_SYSTEM}
    assert "=== PAGE 2 ===" in call["messages"][1]["content"]
    assert call["response_format"]["type"] == "json_schema"
    assert call["response_format"]["json_schema"]["name"] == "ChapterDetectionResult"
    assert call["response_format"]["json_schema"]["schema"] == (
        ChapterDetectionResult.model_json_schema()
    )


def test_compatible_services_get_json_mode_and_the_schema_in_the_instructions() -> None:
    provider, create = openai_provider(completion(json.dumps(CHAPTERS)), json_schema=False)

    provider.extract_chapters(PAGES)

    call = create.calls[0]
    assert call["response_format"] == {"type": "json_object"}
    assert "JSON schema" in call["messages"][0]["content"]
    assert '"start_page"' in call["messages"][0]["content"]


def test_openai_retries_invalid_output_once() -> None:
    provider, create = openai_provider(completion("not json"), completion(json.dumps(CHAPTERS)))

    assert provider.extract_chapters(PAGES).chapters
    assert len(create.calls) == 2


def test_openai_reports_a_cut_off_answer() -> None:
    provider, create = openai_provider(completion('{"chapters": [', finish_reason="length"))

    with pytest.raises(AIResponseError, match="cut off"):
        provider.extract_chapters(PAGES)
    assert len(create.calls) == 1


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (401, "ai_invalid_key"),
        (404, "ai_model_not_found"),
        (429, "ai_quota_exhausted"),
        (500, "ai_provider_error"),
    ],
)
def test_openai_errors_are_translated(status: int, code: str) -> None:
    provider, _ = openai_provider(openai_status_error(status))

    with pytest.raises(AIProviderError) as exc_info:
        provider.extract_chapters(PAGES)
    assert exc_info.value.code == code


def test_openai_chat_sends_system_prompt_and_roles() -> None:
    provider, create = openai_provider(completion("  der Tisch  "))

    assert provider.chat(HISTORY) == "der Tisch"
    messages = create.calls[0]["messages"]
    assert messages[0] == {"role": "system", "content": prompts.CHAT_SYSTEM}
    assert [m["role"] for m in messages[1:]] == ["user", "assistant", "user"]
    assert "response_format" not in create.calls[0]


def test_openai_lists_chat_models_only() -> None:
    provider, _ = openai_provider(ids=["gpt-b", "text-embedding-3-small", "gpt-a", "whisper-1"])

    assert provider.list_models() == ["gpt-a", "gpt-b"]


def test_compatible_services_list_every_model() -> None:
    provider, _ = openai_provider(ids=["deepseek-chat", "some-embedding"], base_url="https://x")

    assert provider.list_models() == ["deepseek-chat", "some-embedding"]


# ---------------------------------------------------------------- Anthropic


def message(*content: Any, stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(content=list(content), stop_reason=stop_reason)


def tool_use(payload: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", name="submit_result", input=payload)


def text(value: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=value)


def anthropic_provider(*outcomes: Any) -> tuple[AnthropicProvider, Recorder]:
    create = Recorder(*outcomes)
    client = SimpleNamespace(
        messages=SimpleNamespace(create=create),
        models=SimpleNamespace(
            list=lambda limit: [SimpleNamespace(id="claude-b"), SimpleNamespace(id="claude-a")]
        ),
    )
    provider = AnthropicProvider(
        api_key="k", model="claude-test", timeout_seconds=5, max_output_tokens=1234, client=client
    )
    return provider, create


def test_anthropic_forces_the_result_tool() -> None:
    provider, create = anthropic_provider(message(tool_use(CHAPTERS)))

    result = provider.extract_chapters(PAGES)

    assert result.chapters[0].start_page == 2
    call = create.calls[0]
    assert call["model"] == "claude-test"
    assert call["max_tokens"] == 1234
    assert call["system"] == prompts.CHAPTER_DETECTION_SYSTEM
    assert call["tool_choice"] == {"type": "tool", "name": "submit_result"}
    assert call["tools"][0]["input_schema"] == ChapterDetectionResult.model_json_schema()


def test_anthropic_retries_when_the_tool_input_is_invalid() -> None:
    provider, create = anthropic_provider(
        message(tool_use({"chapters": [{"title": "x"}]})), message(tool_use(CHAPTERS))
    )

    assert provider.extract_chapters(PAGES).chapters[0].title == "Kapitel 1"
    assert len(create.calls) == 2


def test_anthropic_reports_a_cut_off_answer() -> None:
    provider, _ = anthropic_provider(message(tool_use({}), stop_reason="max_tokens"))

    with pytest.raises(AIResponseError, match="cut off"):
        provider.extract_chapters(PAGES)


def test_anthropic_errors_are_translated() -> None:
    response = httpx.Response(401, request=httpx.Request("POST", "https://api.anthropic.com"))
    provider, _ = anthropic_provider(
        anthropic.APIStatusError("bad key", response=response, body=None)
    )

    with pytest.raises(AIProviderError) as exc_info:
        provider.chat(HISTORY)
    assert exc_info.value.code == "ai_invalid_key"


def test_anthropic_chat_joins_text_blocks() -> None:
    provider, create = anthropic_provider(message(text("der "), text("Tisch")))

    assert provider.chat(HISTORY) == "der Tisch"
    call = create.calls[0]
    assert call["system"] == prompts.CHAT_SYSTEM
    assert [m["role"] for m in call["messages"]] == ["user", "assistant", "user"]
    assert "tools" not in call


def test_anthropic_lists_models() -> None:
    provider, _ = anthropic_provider()

    assert provider.list_models() == ["claude-a", "claude-b"]


# ---------------------------------------------------------------- factory


@pytest.mark.parametrize(
    ("kind", "expected", "base_url"),
    [
        (AIProviderKind.OPENAI, OpenAIProvider, None),
        (AIProviderKind.OPENAI_COMPATIBLE, OpenAIProvider, "https://api.deepseek.com"),
        (AIProviderKind.ANTHROPIC, AnthropicProvider, None),
    ],
)
def test_factory_builds_each_provider(
    kind: AIProviderKind, expected: type, base_url: str | None
) -> None:
    config = AIConfig(provider=kind, model="m", api_key="k", base_url=base_url)

    provider = create_ai_provider(config, Settings(_env_file=None))

    assert isinstance(provider, expected)
    assert provider.model == "m"
    if kind is AIProviderKind.OPENAI_COMPATIBLE:
        assert provider.json_schema is False
        assert str(provider.client.base_url).startswith("https://api.deepseek.com")


def test_config_does_not_show_the_key() -> None:
    config = AIConfig(provider=AIProviderKind.OPENAI, model="m", api_key="sk-secret")

    assert "sk-secret" not in repr(config)
