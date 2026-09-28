from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.db.models import (
    LearningSession,
    LearningSessionItem,
    UserVocabularyProgress,
    VocabularyItem,
)
from app.domain.enums import SessionMode, VocabularyStatus
from app.repositories.chapter_repository import ChapterRepository
from app.repositories.learning_repository import LearningRepository
from app.services.learning.progression import ProgressionPolicy, new_progress


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class SessionItem:
    position: int
    vocabulary_item: VocabularyItem
    progress: UserVocabularyProgress | None


class LearningSessionService:
    """Starts study batches of a chapter and shows their items."""

    def __init__(
        self,
        session: Session,
        *,
        policy: ProgressionPolicy,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.session = session
        self.chapters = ChapterRepository(session)
        self.learning = LearningRepository(session)
        self.policy = policy
        self.clock = clock

    def start(
        self,
        *,
        user_id: int,
        chapter_id: int,
        batch_size: int,
        mode: SessionMode = SessionMode.NEW,
    ) -> LearningSession:
        """Start a batch and mark its words as studied.

        NEW: the chapter's next unstudied words, only once the policy unlocks the next batch.
        REVIEW: studied but not yet mastered words, weak ones first.
        """
        if self.chapters.get(chapter_id) is None:
            raise NotFoundError(
                f"Chapter {chapter_id} was not found.", details={"chapter_id": chapter_id}
            )
        if mode is SessionMode.REVIEW:
            vocabulary = self._review_words(user_id, chapter_id, batch_size)
        else:
            vocabulary = self._new_words(user_id, chapter_id, batch_size)

        now = self.clock()
        existing = self.learning.progress_by_item(
            user_id=user_id, vocabulary_item_ids=(item.id for item in vocabulary)
        )
        learning_session = LearningSession(
            user_id=user_id,
            chapter_id=chapter_id,
            batch_size=batch_size,
            mode=mode,
            correct_count=0,
            wrong_count=0,
            items=[
                LearningSessionItem(vocabulary_item_id=item.id, position=position)
                for position, item in enumerate(vocabulary, start=1)
            ],
        )
        new_records = []
        for item in vocabulary:
            progress = existing.get(item.id)
            if progress is None:
                progress = new_progress(user_id, item.id)
                new_records.append(progress)
            self.policy.record_study(progress, now=now)

        try:
            self.learning.add(learning_session, *new_records)
            self.session.commit()
        except IntegrityError as exc:
            # Another request started a session with the same items at the same time.
            self.session.rollback()
            raise ConflictError(
                "A learning session for these items was started concurrently. Try again.",
                code="concurrent_learning_session",
            ) from exc
        self.session.refresh(learning_session)  # load server-generated started_at
        return learning_session

    def _new_words(
        self, user_id: int, chapter_id: int, batch_size: int
    ) -> Sequence[VocabularyItem]:
        counts = self.learning.status_counts(user_id=user_id, chapter_ids=[chapter_id])[chapter_id]
        if not self.policy.is_new_batch_unlocked(counts):
            raise ConflictError(
                "Master the words you are learning before starting a new batch: "
                "start a review session first.",
                code="batch_locked",
                details={
                    "chapter_id": chapter_id,
                    "learning": counts[VocabularyStatus.LEARNING],
                    "weak": counts[VocabularyStatus.WEAK],
                },
            )
        vocabulary = self.learning.next_new_items(
            user_id=user_id, chapter_id=chapter_id, limit=batch_size
        )
        if not vocabulary:
            raise ConflictError(
                "Every vocabulary item of this chapter has already been studied.",
                code="no_new_vocabulary",
                details={"chapter_id": chapter_id},
            )
        return vocabulary

    def _review_words(
        self, user_id: int, chapter_id: int, batch_size: int
    ) -> Sequence[VocabularyItem]:
        vocabulary = self.learning.review_items(
            user_id=user_id, chapter_id=chapter_id, limit=batch_size
        )
        if not vocabulary:
            raise ConflictError(
                "There is nothing to review in this chapter.",
                code="nothing_to_review",
                details={"chapter_id": chapter_id},
            )
        return vocabulary

    def get(self, *, user_id: int, learning_session_id: int) -> LearningSession:
        learning_session = self.learning.get_session(learning_session_id)
        # Another user's session is reported as missing, not as forbidden.
        if learning_session is None or learning_session.user_id != user_id:
            raise NotFoundError(
                f"Learning session {learning_session_id} was not found.",
                details={"learning_session_id": learning_session_id},
            )
        return learning_session

    def items(self, *, user_id: int, learning_session_id: int) -> list[SessionItem]:
        """The session's vocabulary in display order, with the user's current progress."""
        self.get(user_id=user_id, learning_session_id=learning_session_id)
        rows = self.learning.session_items(learning_session_id)
        progress = self.learning.progress_by_item(
            user_id=user_id, vocabulary_item_ids=(vocabulary.id for _, vocabulary in rows)
        )
        return [
            SessionItem(
                position=item.position,
                vocabulary_item=vocabulary,
                progress=progress.get(vocabulary.id),
            )
            for item, vocabulary in rows
        ]
