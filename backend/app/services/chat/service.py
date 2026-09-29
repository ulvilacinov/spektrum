from collections.abc import Callable, Sequence

from app.core.exceptions import UnprocessableError
from app.domain.entities import ChatMessage
from app.domain.enums import ChatRole
from app.services.ai import AIProvider

# Older messages are dropped: they cost tokens and rarely matter for a quick question.
MAX_HISTORY_MESSAGES = 20


class ChatService:
    """Quick questions to the AI tutor. Stateless: the client sends the recent history."""

    def __init__(self, *, ai_provider_factory: Callable[[], AIProvider]) -> None:
        self.ai_provider_factory = ai_provider_factory

    def reply(self, messages: Sequence[ChatMessage]) -> str:
        if not messages or messages[-1].role != ChatRole.USER:
            raise UnprocessableError(
                "The last message must be the learner's question.", code="invalid_chat"
            )
        recent = list(messages[-MAX_HISTORY_MESSAGES:])
        # A conversation sent to the model starts with the learner.
        while recent[0].role != ChatRole.USER:
            recent.pop(0)
        return self.ai_provider_factory().chat(recent)
