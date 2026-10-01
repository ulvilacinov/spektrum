import logging
from abc import abstractmethod
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ValidationError

from app.domain.entities import ExtractedPage
from app.services.ai import prompts
from app.services.ai.errors import AIResponseError
from app.services.ai.provider import AIProvider
from app.services.ai.schemas import (
    AnswerEvaluationRequest,
    AnswerEvaluationResult,
    ChapterDetectionResult,
    VocabularyExtractionResult,
)

logger = logging.getLogger(__name__)


class StructuredAIProvider(AIProvider):
    """Shared behaviour of the vendor implementations.

    Subclasses send one request and return the raw structured answer (JSON text or an already
    parsed dict); this class validates it against the Pydantic contract and retries once when
    the answer is not valid.
    """

    def __init__(self, *, max_attempts: int = 2) -> None:
        # Extra attempts only for answers that are not valid structured output.
        self.max_attempts = max_attempts

    @abstractmethod
    def _generate_structured(
        self, *, system: str, prompt: str, schema: type[BaseModel]
    ) -> str | dict[str, Any] | None:
        """One request asking for JSON that matches ``schema``.

        Raise ``AIResponseError`` when the answer was cut off (retrying would not help).
        """

    def extract_chapters(self, pages: Sequence[ExtractedPage]) -> ChapterDetectionResult:
        return self._structured(
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
        return self._structured(
            system=prompts.VOCABULARY_EXTRACTION_SYSTEM,
            prompt=prompts.vocabulary_extraction_prompt(chapter_title, pages, next_chapter_title),
            schema=VocabularyExtractionResult,
        )

    def evaluate_answer(self, request: AnswerEvaluationRequest) -> AnswerEvaluationResult:
        return self._structured(
            system=prompts.ANSWER_EVALUATION_SYSTEM,
            prompt=prompts.answer_evaluation_prompt(request),
            schema=AnswerEvaluationResult,
        )

    def _structured[T: BaseModel](self, *, system: str, prompt: str, schema: type[T]) -> T:
        problem = "no attempt made"
        for attempt in range(1, self.max_attempts + 1):
            raw = self._generate_structured(system=system, prompt=prompt, schema=schema)
            if not raw:
                problem = "empty response"
            else:
                try:
                    if isinstance(raw, dict):
                        return schema.model_validate(raw)
                    return schema.model_validate_json(raw)
                except ValidationError as exc:
                    problem = f"invalid structured output: {exc.errors()[:3]}"
            logger.warning(
                "%s attempt %d/%d for %s failed: %s",
                type(self).__name__,
                attempt,
                self.max_attempts,
                schema.__name__,
                problem,
            )
        raise AIResponseError(
            "The AI service did not return valid structured output.",
            details={"reason": problem[:500]},
        )


def truncated_error() -> AIResponseError:
    return AIResponseError(
        "The AI response was cut off because it was too long. "
        "Lower AI_MAX_PAGES_PER_REQUEST and analyze again."
    )
