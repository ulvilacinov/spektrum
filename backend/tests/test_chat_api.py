from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_ai_provider_factory
from app.domain.enums import ChatRole
from app.services.ai import AINotConfiguredError, AIProviderError
from app.services.chat import MAX_HISTORY_MESSAGES
from tests.fake_ai import FakeAIProvider


def user(text: str) -> dict[str, str]:
    return {"role": "user", "content": text}


def assistant(text: str) -> dict[str, str]:
    return {"role": "assistant", "content": text}


def test_answers_the_latest_question_with_the_history(
    client: TestClient, fake_ai: FakeAIProvider
) -> None:
    fake_ai.chat_reply = "**der Tisch**: masa. Çoğulu: die Tische."

    response = client.post(
        "/api/chat",
        json={
            "messages": [
                user("Merhaba"),
                assistant("Merhaba! Ne sormak istersin?"),
                user("  Tisch hangi artikeli alır?  "),
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {"reply": "**der Tisch**: masa. Çoğulu: die Tische."}
    [sent] = fake_ai.chat_calls
    assert [(message.role, message.content) for message in sent] == [
        (ChatRole.USER, "Merhaba"),
        (ChatRole.ASSISTANT, "Merhaba! Ne sormak istersin?"),
        (ChatRole.USER, "Tisch hangi artikeli alır?"),
    ]


def test_sends_only_the_recent_history_starting_with_the_learner(
    client: TestClient, fake_ai: FakeAIProvider
) -> None:
    messages = []
    for index in range(15):
        messages += [user(f"soru {index}"), assistant(f"cevap {index}")]
    messages.append(user("son soru"))

    assert client.post("/api/chat", json={"messages": messages}).status_code == 200

    [sent] = fake_ai.chat_calls
    assert len(sent) <= MAX_HISTORY_MESSAGES
    assert sent[0].role == ChatRole.USER
    assert sent[-1].content == "son soru"


def test_the_last_message_must_be_the_learners(client: TestClient, fake_ai: FakeAIProvider) -> None:
    response = client.post("/api/chat", json={"messages": [user("Merhaba"), assistant("Merhaba!")]})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_chat"
    assert fake_ai.chat_calls == []


@pytest.mark.parametrize(
    "payload",
    [
        {"messages": []},
        {"messages": [user("   ")]},
        {"messages": [{"role": "system", "content": "x"}]},
    ],
)
def test_invalid_requests_are_rejected(client: TestClient, payload: dict) -> None:
    assert client.post("/api/chat", json=payload).status_code == 422


def test_ai_failures_are_reported(client: TestClient, fake_ai: FakeAIProvider) -> None:
    fake_ai.error = AIProviderError("down")

    response = client.post("/api/chat", json={"messages": [user("Hallo")]})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ai_provider_error"


def test_needs_an_ai_configuration(client: TestClient) -> None:
    def not_configured() -> Callable[[], None]:
        def factory() -> None:
            raise AINotConfiguredError("GEMINI_API_KEY is not set.")

        return factory

    client.app.dependency_overrides[get_ai_provider_factory] = not_configured

    response = client.post("/api/chat", json={"messages": [user("Hallo")]})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_not_configured"
