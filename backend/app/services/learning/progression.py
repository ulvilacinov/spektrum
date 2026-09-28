"""The single place that decides how a learner's vocabulary status changes.

Swap ``ProgressionPolicy`` for another implementation (e.g. spaced repetition) without
touching sessions, quizzes or routes.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import datetime

from app.db.models import UserVocabularyProgress
from app.domain.enums import VocabularyStatus


def new_progress(user_id: int, vocabulary_item_id: int) -> UserVocabularyProgress:
    """A fresh progress record with every counter set (ORM defaults apply only on flush)."""
    return UserVocabularyProgress(
        user_id=user_id,
        vocabulary_item_id=vocabulary_item_id,
        status=VocabularyStatus.NEW,
        seen_count=0,
        correct_count=0,
        wrong_count=0,
        consecutive_correct=0,
        mastery_score=0.0,
    )


class ProgressionPolicy(ABC):
    @abstractmethod
    def record_study(self, progress: UserVocabularyProgress, *, now: datetime) -> None:
        """The learner was shown the item in a learning session."""

    @abstractmethod
    def record_answer(
        self, progress: UserVocabularyProgress, *, correct: bool, now: datetime
    ) -> None:
        """The learner answered a quiz question about the item."""

    @abstractmethod
    def is_new_batch_unlocked(self, status_counts: Mapping[VocabularyStatus, int]) -> bool:
        """Whether the chapter's next batch of new words may start, given its status counts."""


class SimpleProgressionPolicy(ProgressionPolicy):
    """MVP rules from the spec.

    new → learning after the first study; a wrong answer → weak (due for review now);
    a correct answer → learning; ``mastery_streak`` correct answers in a row → mastered.
    The next batch unlocks once every studied word of the chapter is mastered.
    """

    def __init__(self, mastery_streak: int = 2) -> None:
        self.mastery_streak = mastery_streak

    def record_study(self, progress: UserVocabularyProgress, *, now: datetime) -> None:
        progress.seen_count += 1
        progress.last_seen_at = now
        if progress.status is VocabularyStatus.NEW:
            progress.status = VocabularyStatus.LEARNING

    def record_answer(
        self, progress: UserVocabularyProgress, *, correct: bool, now: datetime
    ) -> None:
        progress.last_seen_at = now
        if correct:
            progress.correct_count += 1
            progress.consecutive_correct += 1
            if progress.consecutive_correct >= self.mastery_streak:
                progress.status = VocabularyStatus.MASTERED
            else:
                progress.status = VocabularyStatus.LEARNING
            progress.next_review_at = None
        else:
            progress.wrong_count += 1
            progress.consecutive_correct = 0
            progress.status = VocabularyStatus.WEAK
            progress.next_review_at = now
        progress.mastery_score = min(progress.consecutive_correct / self.mastery_streak, 1.0)

    def is_new_batch_unlocked(self, status_counts: Mapping[VocabularyStatus, int]) -> bool:
        open_words = status_counts.get(VocabularyStatus.LEARNING, 0) + status_counts.get(
            VocabularyStatus.WEAK, 0
        )
        return open_words == 0
