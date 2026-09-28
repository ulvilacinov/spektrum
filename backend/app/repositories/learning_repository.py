from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import datetime

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from app.db.models import (
    Chapter,
    LearningSession,
    LearningSessionItem,
    QuizQuestion,
    UserVocabularyProgress,
    VocabularyItem,
)
from app.domain.enums import ErrorType, EvaluationMethod, VocabularyStatus


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

    def question_with_context(
        self, question_id: int
    ) -> tuple[QuizQuestion, LearningSession, VocabularyItem] | None:
        statement = (
            select(QuizQuestion, LearningSession, VocabularyItem)
            .join(LearningSession, LearningSession.id == QuizQuestion.learning_session_id)
            .join(VocabularyItem, VocabularyItem.id == QuizQuestion.vocabulary_item_id)
            .where(QuizQuestion.id == question_id)
        )
        row = self.session.execute(statement).one_or_none()
        return None if row is None else (row[0], row[1], row[2])

    def record_answer(
        self,
        question_id: int,
        *,
        user_answer: str,
        is_correct: bool,
        score: float,
        corrected_answer: str,
        ai_feedback: str,
        error_type: ErrorType | None,
        evaluation_method: EvaluationMethod,
        answered_at: datetime,
    ) -> bool:
        """Store the answer unless the question already has one (single conditional UPDATE)."""
        result = self.session.execute(
            update(QuizQuestion)
            .where(QuizQuestion.id == question_id, QuizQuestion.user_answer.is_(None))
            .values(
                user_answer=user_answer,
                is_correct=is_correct,
                score=score,
                corrected_answer=corrected_answer,
                ai_feedback=ai_feedback,
                error_type=error_type,
                evaluation_method=evaluation_method,
                answered_at=answered_at,
            )
        )
        return result.rowcount == 1

    def unanswered_question_count(self, learning_session_id: int) -> int:
        statement = select(func.count(QuizQuestion.id)).where(
            QuizQuestion.learning_session_id == learning_session_id,
            QuizQuestion.user_answer.is_(None),
        )
        return self.session.scalar(statement) or 0

    def status_counts(
        self, *, user_id: int, chapter_ids: Iterable[int]
    ) -> dict[int, Counter[VocabularyStatus]]:
        """Per chapter, how many words have each status (words without progress are new)."""
        ids = list(chapter_ids)
        if not ids:
            return {}
        progress = UserVocabularyProgress
        statement = (
            select(VocabularyItem.chapter_id, progress.status, func.count(VocabularyItem.id))
            .outerjoin(
                progress,
                and_(
                    progress.vocabulary_item_id == VocabularyItem.id,
                    progress.user_id == user_id,
                ),
            )
            .where(VocabularyItem.chapter_id.in_(ids))
            .group_by(VocabularyItem.chapter_id, progress.status)
        )
        counts: dict[int, Counter[VocabularyStatus]] = {chapter_id: Counter() for chapter_id in ids}
        for chapter_id, status, count in self.session.execute(statement):
            counts[chapter_id][status or VocabularyStatus.NEW] += count
        return counts

    def review_items(
        self, *, user_id: int, chapter_id: int, limit: int
    ) -> Sequence[VocabularyItem]:
        """Studied, not yet mastered words: weak first (longest due first), then learning."""
        progress = UserVocabularyProgress
        weak_first = (progress.status == VocabularyStatus.WEAK).desc()
        statement = (
            select(VocabularyItem)
            .join(
                progress,
                and_(
                    progress.vocabulary_item_id == VocabularyItem.id,
                    progress.user_id == user_id,
                ),
            )
            .where(
                VocabularyItem.chapter_id == chapter_id,
                progress.status.in_([VocabularyStatus.WEAK, VocabularyStatus.LEARNING]),
            )
            .order_by(
                weak_first,
                progress.next_review_at.asc().nulls_last(),
                progress.last_seen_at.asc().nulls_first(),
                VocabularyItem.order,
            )
            .limit(limit)
        )
        return self.session.scalars(statement).all()

    def weak_items(
        self,
        *,
        user_id: int,
        document_id: int | None,
        chapter_id: int | None,
        limit: int,
    ) -> Sequence[tuple[VocabularyItem, UserVocabularyProgress]]:
        progress = UserVocabularyProgress
        statement = (
            select(VocabularyItem, progress)
            .join(progress, progress.vocabulary_item_id == VocabularyItem.id)
            .join(Chapter, Chapter.id == VocabularyItem.chapter_id)
            .where(progress.user_id == user_id, progress.status == VocabularyStatus.WEAK)
            .order_by(progress.next_review_at.asc().nulls_last(), VocabularyItem.id)
            .limit(limit)
        )
        if document_id is not None:
            statement = statement.where(Chapter.document_id == document_id)
        if chapter_id is not None:
            statement = statement.where(VocabularyItem.chapter_id == chapter_id)
        return [(item, row) for item, row in self.session.execute(statement)]

    def last_wrong_answers(
        self, *, user_id: int, vocabulary_item_ids: Iterable[int]
    ) -> dict[int, QuizQuestion]:
        """The most recent wrong answer of the user for each item."""
        ids = list(vocabulary_item_ids)
        if not ids:
            return {}
        statement = (
            select(QuizQuestion)
            .join(LearningSession, LearningSession.id == QuizQuestion.learning_session_id)
            .where(
                LearningSession.user_id == user_id,
                QuizQuestion.vocabulary_item_id.in_(ids),
                QuizQuestion.is_correct.is_(False),
            )
            .order_by(QuizQuestion.answered_at.desc(), QuizQuestion.id.desc())
        )
        latest: dict[int, QuizQuestion] = {}
        for question in self.session.scalars(statement):
            latest.setdefault(question.vocabulary_item_id, question)
        return latest
