from collections import Counter
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models import Chapter, QuizQuestion, UserVocabularyProgress, VocabularyItem
from app.domain.enums import VocabularyStatus
from app.repositories.chapter_repository import ChapterRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.learning_repository import LearningRepository
from app.services.learning.progression import ProgressionPolicy


@dataclass(frozen=True, slots=True)
class ChapterProgress:
    chapter: Chapter
    counts: Counter[VocabularyStatus]
    next_batch_unlocked: bool

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    @property
    def can_start_new_batch(self) -> bool:
        return self.next_batch_unlocked and self.counts[VocabularyStatus.NEW] > 0

    @property
    def can_review(self) -> bool:
        return self.counts[VocabularyStatus.LEARNING] + self.counts[VocabularyStatus.WEAK] > 0


@dataclass(frozen=True, slots=True)
class WeakWord:
    vocabulary_item: VocabularyItem
    progress: UserVocabularyProgress
    last_mistake: QuizQuestion | None


class ProgressService:
    """Read-only views of a learner's progress. Status rules stay in ProgressionPolicy."""

    def __init__(self, session: Session, *, policy: ProgressionPolicy) -> None:
        self.documents = DocumentRepository(session)
        self.chapters = ChapterRepository(session)
        self.learning = LearningRepository(session)
        self.policy = policy

    def chapter_progress(
        self, *, user_id: int, document_id: int | None = None
    ) -> list[ChapterProgress]:
        self._require_document(document_id)
        chapters = self.chapters.list_chapters(document_id=document_id)
        counts = self.learning.status_counts(
            user_id=user_id, chapter_ids=(chapter.id for chapter in chapters)
        )
        return [
            ChapterProgress(
                chapter=chapter,
                counts=counts[chapter.id],
                next_batch_unlocked=self.policy.is_new_batch_unlocked(counts[chapter.id]),
            )
            for chapter in chapters
        ]

    def weak_words(
        self,
        *,
        user_id: int,
        document_id: int | None = None,
        chapter_id: int | None = None,
        limit: int = 50,
    ) -> list[WeakWord]:
        """Weak words, longest due first, each with the learner's latest mistake."""
        self._require_document(document_id)
        if chapter_id is not None and self.chapters.get(chapter_id) is None:
            raise NotFoundError(
                f"Chapter {chapter_id} was not found.", details={"chapter_id": chapter_id}
            )
        rows = self.learning.weak_items(
            user_id=user_id, document_id=document_id, chapter_id=chapter_id, limit=limit
        )
        mistakes = self.learning.last_wrong_answers(
            user_id=user_id, vocabulary_item_ids=(item.id for item, _ in rows)
        )
        return [
            WeakWord(vocabulary_item=item, progress=progress, last_mistake=mistakes.get(item.id))
            for item, progress in rows
        ]

    def _require_document(self, document_id: int | None) -> None:
        if document_id is not None and self.documents.get(document_id) is None:
            raise NotFoundError(
                f"Document {document_id} was not found.", details={"document_id": document_id}
            )
