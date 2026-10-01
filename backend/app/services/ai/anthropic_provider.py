from collections.abc import Sequence
from typing import Any

import anthropic
from pydantic import BaseModel

from app.domain.entities import ChatMessage
from app.domain.enums import ChatRole
from app.services.ai import prompts
from app.services.ai.base import StructuredAIProvider, truncated_error
from app.services.ai.errors import AIResponseError, provider_error

_TOOL_NAME = "submit_result"
CHAT_MAX_TOKENS = 2048


class AnthropicProvider(StructuredAIProvider):
    """Anthropic's Messages API. Structured output is a forced call of a tool whose input
    schema is the expected result, so the model has to answer with matching JSON."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int,
        max_output_tokens: int,
        max_attempts: int = 2,
        client: Any | None = None,
    ) -> None:
        super().__init__(max_attempts=max_attempts)
        self.model = model
        self.max_output_tokens = max_output_tokens
        # The SDK retries 429, 529 (overloaded) and 5xx answers with backoff.
        self.client = client or anthropic.Anthropic(
            api_key=api_key, timeout=timeout_seconds, max_retries=3
        )

    def _generate_structured(
        self, *, system: str, prompt: str, schema: type[BaseModel]
    ) -> dict[str, Any] | None:
        response = self._create(
            max_tokens=self.max_output_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "name": _TOOL_NAME,
                    "description": "Return the result in the required structure.",
                    "input_schema": schema.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
        )
        if response.stop_reason == "max_tokens":
            raise truncated_error()
        for block in response.content:
            if block.type == "tool_use" and block.name == _TOOL_NAME:
                return block.input
        return None

    def chat(self, messages: Sequence[ChatMessage]) -> str:
        response = self._create(
            max_tokens=CHAT_MAX_TOKENS,
            system=prompts.CHAT_SYSTEM,
            messages=[
                {
                    "role": "user" if message.role == ChatRole.USER else "assistant",
                    "content": message.content,
                }
                for message in messages
            ],
        )
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        if not text:
            raise AIResponseError("The AI service returned an empty answer.")
        return text

    def list_models(self) -> list[str]:
        try:
            return sorted(model.id for model in self.client.models.list(limit=100))
        except anthropic.APIStatusError as exc:
            raise provider_error(exc.status_code, exc) from exc
        except anthropic.APIError as exc:
            raise provider_error(None, exc) from exc

    def _create(self, **kwargs: Any) -> Any:
        try:
            return self.client.messages.create(model=self.model, **kwargs)
        except anthropic.APIStatusError as exc:
            raise provider_error(exc.status_code, exc) from exc
        except anthropic.APIError as exc:  # connection errors, timeouts
            raise provider_error(None, exc) from exc
