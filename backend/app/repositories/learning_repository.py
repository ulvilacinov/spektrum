from collections.abc import Iterable, Sequence

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    LearningSession,
    LearningSessionItem,
    QuizQuestion,
    UserVocabularyProgress,
    VocabularyItem,
)
from app.domain.enums import VocabularyStatus


class LearningRepository:
    """Database access for learning sessions and vocabulary progress. Never commits."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def next_new_items(
        self, *, user_id: int, chapter_id: int, limit: int
    ) -> Sequence[VocabularyItem]:
        """The chapter's next items (in PDF order) that the user has not studied yet."""
        progress = UserVocabularyProgress
        statement = (
            select(VocabularyItem)
            .outerjoin(
                progress,
                and_(
                    progress.vocabulary_item_id == VocabularyItem.id,
                    progress.user_id == user_id,
                ),
            )
            .where(
                VocabularyItem.chapter_id == chapter_id,
                or_(progress.id.is_(None), progress.status == VocabularyStatus.NEW),
            )
            .order_by(VocabularyItem.order)
            .limit(limit)
        )
        return self.session.scalars(statement).all()

    def progress_by_item(
        self, *, user_id: int, vocabulary_item_ids: Iterable[int]
    ) -> dict[int, UserVocabularyProgress]:
        ids = list(vocabulary_item_ids)
        if not ids:
            return {}
        statement = select(UserVocabularyProgress).where(
            UserVocabularyProgress.user_id == user_id,
            UserVocabularyProgress.vocabulary_item_id.in_(ids),
        )
        return {row.vocabulary_item_id: row for row in self.session.scalars(statement)}

    def add(self, *objects: LearningSession | UserVocabularyProgress | QuizQuestion) -> None:
        self.session.add_all(objects)
        self.session.flush()

    def get_session(self, learning_session_id: int) -> LearningSession | None:
        return self.session.get(LearningSession, learning_session_id)

    def session_items(
        self, learning_session_id: int
    ) -> Sequence[tuple[LearningSessionItem, VocabularyItem]]:
        statement = (
            select(LearningSessionItem, VocabularyItem)
            .join(VocabularyItem, VocabularyItem.id == LearningSessionItem.vocabulary_item_id)
            .where(LearningSessionItem.learning_session_id == learning_session_id)
            .order_by(LearningSessionItem.position)
        )
        return [(item, vocabulary) for item, vocabulary in self.session.execute(statement)]

    def quiz_questions(self, learning_session_id: int) -> Sequence[QuizQuestion]:
        statement = (
            select(QuizQuestion)
            .where(QuizQuestion.learning_session_id == learning_session_id)
            .order_by(QuizQuestion.position)
        )
        return self.session.scalars(statement).all()
