from collections.abc import Sequence
from typing import Any

from app.domain.entities import ExtractedPage
from app.domain.enums import VocabularyItemType
from app.services.ai import AIProvider
from app.services.ai.schemas import (
    AnswerEvaluationRequest,
    AnswerEvaluationResult,
    ChapterDetectionResult,
    DetectedChapter,
    ExtractedVocabularyItem,
    VocabularyExtractionResult,
    VocabularySection,
)


def chapter(number: int | None, start_page: int, title: str | None = None) -> DetectedChapter:
    return DetectedChapter(
        title=title or f"Kapitel {number}", chapter_number=number, start_page=start_page
    )


def vocab(german: str, turkish: str, page: int, **fields: Any) -> ExtractedVocabularyItem:
    fields.setdefault("item_type", VocabularyItemType.WORD)
    fields.setdefault("source_text", german)
    return ExtractedVocabularyItem(german=german, turkish=turkish, source_page=page, **fields)


class FakeAIProvider(AIProvider):
    """Deterministic provider for tests.

    ``vocabulary`` maps a chapter title to items; each call returns the items whose
    ``source_page`` is among the pages sent, like a real model would.
    """

    def __init__(self) -> None:
        self.chapters: list[DetectedChapter] = []
        self.vocabulary: dict[str, list[ExtractedVocabularyItem]] = {}
        self.error: Exception | None = None
        self.chapter_calls: list[list[int]] = []
        self.vocabulary_calls: list[tuple[str, list[int], str | None]] = []
        self.evaluation: AnswerEvaluationResult | None = None
        self.evaluation_calls: list[AnswerEvaluationRequest] = []

    def extract_chapters(self, pages: Sequence[ExtractedPage]) -> ChapterDetectionResult:
        self.chapter_calls.append([page.page_number for page in pages])
        if self.error:
            raise self.error
        return ChapterDetectionResult(chapters=self.chapters)

    def extract_vocabulary(
        self,
        chapter_title: str,
        pages: Sequence[ExtractedPage],
        next_chapter_title: str | None = None,
    ) -> VocabularyExtractionResult:
        page_numbers = [page.page_number for page in pages]
        self.vocabulary_calls.append((chapter_title, page_numbers, next_chapter_title))
        items = [
            item
            for item in self.vocabulary.get(chapter_title, [])
            if item.source_page in page_numbers
        ]
        return VocabularyExtractionResult(
            chapter_title=chapter_title, sections=[VocabularySection(name=None, items=items)]
        )

    def evaluate_answer(self, request: AnswerEvaluationRequest) -> AnswerEvaluationResult:
        """Returns ``self.evaluation``; by default judges the answer as wrong in meaning."""
        self.evaluation_calls.append(request)
        if self.error:
            raise self.error
        return self.evaluation or AnswerEvaluationResult(
            is_correct=False,
            score=0.0,
            corrected_answer=request.expected_answer,
            explanation="Anlam yanlış.",
            error_type="meaning",
        )
