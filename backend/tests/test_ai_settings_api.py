import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_ai_provider,
    get_ai_provider_factory,
    get_current_user_id,
    get_provider_builder,
)
from app.core.config import Settings
from app.core.crypto import SecretBox
from app.db.models import User, UserAISettings
from app.main import create_app
from app.services.ai import AIConfig, AIProviderError
from tests.fake_ai import FakeAIProvider

OPENAI = {"provider": "openai", "model": "gpt-test", "api_key": "sk-test-1234"}


@pytest.fixture
def built(client: TestClient, fake_ai: FakeAIProvider) -> list[AIConfig]:
    """Every AI configuration the app builds a provider from (the provider is the fake)."""
    configs: list[AIConfig] = []

    def builder(config: AIConfig) -> FakeAIProvider:
        configs.append(config)
        return fake_ai

    client.app.dependency_overrides[get_provider_builder] = lambda: builder
    return configs


@pytest.fixture
def real_ai_lookup(client: TestClient) -> TestClient:
    """AI endpoints resolve the provider from the user's saved settings, as in production."""
    del client.app.dependency_overrides[get_ai_provider]
    del client.app.dependency_overrides[get_ai_provider_factory]
    return client


def save(client: TestClient, **fields: object):
    return client.put("/api/ai-settings", json=OPENAI | fields)


def test_nothing_is_configured_at_first(client: TestClient) -> None:
    assert client.get("/api/ai-settings").json() == {
        "configured": False,
        "provider": None,
        "model": None,
        "base_url": None,
        "api_key_hint": None,
        "updated_at": None,
    }


def test_saving_stores_the_key_encrypted_and_never_returns_it(
    client: TestClient, built: list[AIConfig], sqlite_session: Session
) -> None:
    response = save(client)

    assert response.status_code == 200
    body = response.json()
    assert body | {"updated_at": None} == {
        "configured": True,
        "provider": "openai",
        "model": "gpt-test",
        "base_url": None,
        "api_key_hint": "1234",
        "updated_at": None,
    }
    assert "sk-test" not in response.text
    assert "sk-test" not in client.get("/api/ai-settings").text
    stored = sqlite_session.query(UserAISettings).one()
    assert "sk-test" not in stored.api_key_encrypted
    assert SecretBox.from_settings(Settings()).decrypt(stored.api_key_encrypted) == "sk-test-1234"


def test_the_key_is_needed_the_first_time(client: TestClient) -> None:
    response = save(client, api_key=None)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ai_api_key_required"


def test_changing_the_model_keeps_the_saved_key(
    real_ai_lookup: TestClient, built: list[AIConfig]
) -> None:
    save(real_ai_lookup)

    assert save(real_ai_lookup, model="gpt-other", api_key="").status_code == 200

    real_ai_lookup.post("/api/chat", json={"messages": [{"role": "user", "content": "Hallo"}]})
    assert built[-1] == AIConfig(
        provider="openai", model="gpt-other", api_key="sk-test-1234", base_url=None
    )


def test_another_provider_needs_its_own_key(client: TestClient) -> None:
    save(client)

    response = save(client, provider="anthropic", model="claude-x", api_key=None)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ai_api_key_required"


@pytest.mark.parametrize("base_url", [None, "http://10.0.0.1/v1", "ftp://x", "https://"])
def test_compatible_services_need_an_https_url(client: TestClient, base_url: str | None) -> None:
    response = save(client, provider="openai_compatible", base_url=base_url)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ai_invalid_base_url"


def test_compatible_service_url_is_kept_and_other_providers_drop_it(client: TestClient) -> None:
    compatible = save(
        client,
        provider="openai_compatible",
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1/",
    )
    assert compatible.json()["base_url"] == "https://api.deepseek.com/v1"

    openai = save(client, base_url="https://ignored.example")
    assert openai.json()["base_url"] is None


def test_a_model_is_required(client: TestClient) -> None:
    assert save(client, model="  ").json()["error"]["code"] == "ai_model_required"


def test_ai_features_are_off_until_settings_are_saved(real_ai_lookup: TestClient) -> None:
    response = real_ai_lookup.post(
        "/api/chat", json={"messages": [{"role": "user", "content": "Hallo"}]}
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_not_configured"


def test_ai_features_use_the_saved_settings(
    real_ai_lookup: TestClient, built: list[AIConfig], fake_ai: FakeAIProvider
) -> None:
    save(real_ai_lookup, provider="anthropic", model="claude-x", api_key="sk-ant-9999")

    response = real_ai_lookup.post(
        "/api/chat", json={"messages": [{"role": "user", "content": "Hallo"}]}
    )

    assert response.status_code == 200
    assert built[-1] == AIConfig(provider="anthropic", model="claude-x", api_key="sk-ant-9999")
    assert fake_ai.chat_calls


def test_deleting_turns_the_ai_off(real_ai_lookup: TestClient, built: list[AIConfig]) -> None:
    save(real_ai_lookup)

    assert real_ai_lookup.delete("/api/ai-settings").status_code == 204

    assert real_ai_lookup.get("/api/ai-settings").json()["configured"] is False
    chat = real_ai_lookup.post("/api/chat", json={"messages": [{"role": "user", "content": "x"}]})
    assert chat.status_code == 503


def test_a_changed_secret_key_means_entering_the_key_again(
    real_ai_lookup: TestClient, built: list[AIConfig], sqlite_session: Session
) -> None:
    save(real_ai_lookup)
    stored = sqlite_session.query(UserAISettings).one()
    stored.api_key_encrypted = SecretBox("another-secret").encrypt("sk-test-1234")
    sqlite_session.commit()

    chat = real_ai_lookup.post("/api/chat", json={"messages": [{"role": "user", "content": "x"}]})

    assert chat.json()["error"]["code"] == "ai_not_configured"


def test_models_can_be_listed_with_an_entered_key(
    client: TestClient, built: list[AIConfig]
) -> None:
    response = client.post(
        "/api/ai-settings/models", json={"provider": "gemini", "api_key": "AI-new-key"}
    )

    assert response.json() == {"models": ["fake-small", "fake-large"]}
    assert built[-1] == AIConfig(provider="gemini", model="", api_key="AI-new-key")


def test_models_can_be_listed_with_the_saved_key(client: TestClient, built: list[AIConfig]) -> None:
    save(client)

    assert client.post("/api/ai-settings/models", json={"provider": "openai"}).status_code == 200
    assert built[-1].api_key == "sk-test-1234"


def test_connection_test_sends_one_tiny_chat_and_saves_nothing(
    client: TestClient, built: list[AIConfig], fake_ai: FakeAIProvider
) -> None:
    fake_ai.chat_reply = "OK"

    response = client.post("/api/ai-settings/test", json=OPENAI)

    assert response.json() == {"reply": "OK"}
    assert "OK" in fake_ai.chat_calls[0][0].content
    assert client.get("/api/ai-settings").json()["configured"] is False


def test_connection_test_reports_a_rejected_key(
    client: TestClient, built: list[AIConfig], fake_ai: FakeAIProvider
) -> None:
    fake_ai.error = AIProviderError("rejected", code="ai_invalid_key")

    response = client.post("/api/ai-settings/test", json=OPENAI)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ai_invalid_key"


def test_settings_are_per_user(
    client: TestClient, built: list[AIConfig], sqlite_session: Session
) -> None:
    save(client)
    sqlite_session.add(User(id=2, username="bob", password_hash=""))
    sqlite_session.commit()

    client.app.dependency_overrides[get_current_user_id] = lambda: 2

    assert client.get("/api/ai-settings").json()["configured"] is False
    listing = client.post("/api/ai-settings/models", json={"provider": "openai"})
    assert listing.json()["error"]["code"] == "ai_api_key_required"


@pytest.mark.parametrize("secret_key", [None, "", "   "])
def test_production_refuses_to_start_without_a_secret_key(secret_key: str | None) -> None:
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(Settings(_env_file=None, environment="production", secret_key=secret_key))


def test_secret_box_round_trip() -> None:
    box = SecretBox("s3cret")
    token = box.encrypt("sk-abc")

    assert token != "sk-abc"
    assert box.decrypt(token) == "sk-abc"
    assert SecretBox("other").decrypt(token) is None
