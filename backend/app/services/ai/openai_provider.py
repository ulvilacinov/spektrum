import json
from collections.abc import Sequence
from typing import Any

import openai
from pydantic import BaseModel

from app.domain.entities import ChatMessage
from app.domain.enums import ChatRole
from app.services.ai import prompts
from app.services.ai.base import StructuredAIProvider, truncated_error
from app.services.ai.errors import AIResponseError, provider_error

# Not chat models; hidden from the model list of the official OpenAI API.
_NON_CHAT_MARKERS = (
    "embedding",
    "tts",
    "whisper",
    "dall-e",
    "audio",
    "realtime",
    "transcribe",
    "image",
    "moderation",
    "search",
    "davinci",
    "babbage",
)


class OpenAIProvider(StructuredAIProvider):
    """OpenAI's Chat Completions API, and any service that offers the same API.

    ``json_schema=True`` (OpenAI itself) asks for output that follows the schema. Compatible
    services (DeepSeek, OpenRouter, Groq, ...) often only support plain JSON mode, so they get
    the schema in the instructions instead; the answer is validated either way.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int,
        base_url: str | None = None,
        json_schema: bool = True,
        max_attempts: int = 2,
        client: Any | None = None,
    ) -> None:
        super().__init__(max_attempts=max_attempts)
        self.model = model
        self.json_schema = json_schema
        self.official = base_url is None
        # The SDK retries 429 and 5xx answers with backoff.
        self.client = client or openai.OpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout_seconds, max_retries=3
        )

    def _generate_structured(
        self, *, system: str, prompt: str, schema: type[BaseModel]
    ) -> str | None:
        json_schema = schema.model_json_schema()
        if self.json_schema:
            response_format: dict[str, Any] = {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": json_schema, "strict": False},
            }
        else:
            response_format = {"type": "json_object"}
            system = (
                f"{system}\nAnswer with a single JSON object that matches this JSON schema:\n"
                f"{json.dumps(json_schema, ensure_ascii=False)}"
            )
        response = self._create(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            response_format=response_format,
        )
        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise truncated_error()
        return choice.message.content

    def chat(self, messages: Sequence[ChatMessage]) -> str:
        response = self._create(
            messages=[
                {"role": "system", "content": prompts.CHAT_SYSTEM},
                *(
                    {
                        "role": "user" if message.role == ChatRole.USER else "assistant",
                        "content": message.content,
                    }
                    for message in messages
                ),
            ]
        )
        text = (response.choices[0].message.content or "").strip()
        if not text:
            raise AIResponseError("The AI service returned an empty answer.")
        return text

    def list_models(self) -> list[str]:
        try:
            ids = [model.id for model in self.client.models.list()]
        except openai.APIStatusError as exc:
            raise provider_error(exc.status_code, exc) from exc
        except openai.APIError as exc:
            raise provider_error(None, exc) from exc
        if self.official:
            ids = [
                model_id
                for model_id in ids
                if not any(marker in model_id for marker in _NON_CHAT_MARKERS)
            ]
        return sorted(ids)

    def _create(self, **kwargs: Any) -> Any:
        try:
            return self.client.chat.completions.create(model=self.model, **kwargs)
        except openai.APIStatusError as exc:
            raise provider_error(exc.status_code, exc) from exc
        except openai.APIError as exc:  # connection errors, timeouts
            raise provider_error(None, exc) from exc
