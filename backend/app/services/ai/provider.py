from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.entities import ExtractedPage
from app.services.ai.schemas import (
    AnswerEvaluationRequest,
    AnswerEvaluationResult,
    ChapterDetectionResult,
    VocabularyExtractionResult,
)


class AIProvider(ABC):
    """The only AI entry point for business logic. Implementations wrap a concrete vendor.

    Methods return validated structured output or raise ``AIProviderError``. Example
    generation is added when a feature needs it.
    """

    @abstractmethod
    def extract_chapters(self, pages: Sequence[ExtractedPage]) -> ChapterDetectionResult:
        """Detect chapter headings and the page each chapter starts on."""

    @abstractmethod
    def extract_vocabulary(
        self,
        chapter_title: str,
        pages: Sequence[ExtractedPage],
        next_chapter_title: str | None = None,
    ) -> VocabularyExtractionResult:
        """Extract the vocabulary items of one chapter from (a part of) its pages."""

    @abstractmethod
    def evaluate_answer(self, request: AnswerEvaluationRequest) -> AnswerEvaluationResult:
        """Grade a free-form quiz answer and explain mistakes in Turkish."""
