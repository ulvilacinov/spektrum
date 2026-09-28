from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from typing import Self

from pydantic import BaseModel

from app.domain.enums import ErrorType, QuestionType, VocabularyStatus
from app.schemas.vocabulary import VocabularyItemRead
from app.services.learning import ChapterProgress, WeakWord


class StatusCounts(BaseModel):
    total: int
    new: int
    learning: int
    weak: int
    mastered: int
    mastery_ratio: float

    @classmethod
    def from_counts(cls, counts: Counter[VocabularyStatus]) -> dict:
        total = sum(counts.values())
        return {
            "total": total,
            "new": counts[VocabularyStatus.NEW],
            "learning": counts[VocabularyStatus.LEARNING],
            "weak": counts[VocabularyStatus.WEAK],
            "mastered": counts[VocabularyStatus.MASTERED],
            "mastery_ratio": round(counts[VocabularyStatus.MASTERED] / total, 4) if total else 0.0,
        }


class ChapterProgressRead(StatusCounts):
    chapter_id: int
    document_id: int
    chapter_number: int | None
    title: str
    can_start_new_batch: bool
    can_review: bool

    @classmethod
    def from_progress(cls, progress: ChapterProgress) -> Self:
        return cls(
            chapter_id=progress.chapter.id,
            document_id=progress.chapter.document_id,
            chapter_number=progress.chapter.chapter_number,
            title=progress.chapter.title,
            can_start_new_batch=progress.can_start_new_batch,
            can_review=progress.can_review,
            **StatusCounts.from_counts(progress.counts),
        )


class ProgressRead(StatusCounts):
    chapters: list[ChapterProgressRead]

    @classmethod
    def from_chapters(cls, chapters: Sequence[ChapterProgress]) -> Self:
        total: Counter[VocabularyStatus] = Counter()
        for chapter in chapters:
            total.update(chapter.counts)
        return cls(
            chapters=[ChapterProgressRead.from_progress(chapter) for chapter in chapters],
            **StatusCounts.from_counts(total),
        )


class WordProgressRead(BaseModel):
    status: VocabularyStatus
    seen_count: int
    correct_count: int
    wrong_count: int
    consecutive_correct: int
    mastery_score: float
    last_seen_at: datetime | None
    next_review_at: datetime | None


class MistakeRead(BaseModel):
    """The learner's latest wrong answer, to explain the mistake."""

    question_id: int
    question_type: QuestionType
    question: str
    user_answer: str | None
    expected_answer: str
    corrected_answer: str | None
    feedback: str | None
    error_type: ErrorType | None
    answered_at: datetime | None


class WeakWordRead(BaseModel):
    vocabulary_item: VocabularyItemRead
    progress: WordProgressRead
    last_mistake: MistakeRead | None

    @classmethod
    def from_weak_word(cls, word: WeakWord) -> Self:
        mistake = word.last_mistake
        return cls(
            vocabulary_item=VocabularyItemRead.model_validate(word.vocabulary_item),
            progress=WordProgressRead.model_validate(word.progress, from_attributes=True),
            last_mistake=None
            if mistake is None
            else MistakeRead(
                question_id=mistake.id,
                question_type=mistake.question_type,
                question=mistake.question,
                user_answer=mistake.user_answer,
                expected_answer=mistake.expected_answer,
                corrected_answer=mistake.corrected_answer,
                feedback=mistake.ai_feedback,
                error_type=mistake.error_type,
                answered_at=mistake.answered_at,
            ),
        )
