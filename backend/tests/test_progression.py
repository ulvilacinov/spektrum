from datetime import UTC, datetime, timedelta

from app.domain.enums import VocabularyStatus
from app.services.learning import SimpleProgressionPolicy, new_progress

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
policy = SimpleProgressionPolicy()


def test_first_study_moves_new_to_learning() -> None:
    progress = new_progress(user_id=1, vocabulary_item_id=7)

    policy.record_study(progress, now=NOW)

    assert progress.status is VocabularyStatus.LEARNING
    assert progress.seen_count == 1
    assert progress.last_seen_at == NOW


def test_studying_again_keeps_weak_and_mastered_status() -> None:
    for status in (VocabularyStatus.WEAK, VocabularyStatus.MASTERED):
        progress = new_progress(1, 7)
        progress.status = status

        policy.record_study(progress, now=NOW)

        assert progress.status is status
        assert progress.seen_count == 1


def test_wrong_answer_makes_the_item_weak_and_due_now() -> None:
    progress = new_progress(1, 7)
    policy.record_study(progress, now=NOW)

    policy.record_answer(progress, correct=False, now=NOW)

    assert progress.status is VocabularyStatus.WEAK
    assert (progress.wrong_count, progress.consecutive_correct) == (1, 0)
    assert progress.next_review_at == NOW
    assert progress.mastery_score == 0.0


def test_one_correct_answer_is_learning_two_in_a_row_is_mastered() -> None:
    progress = new_progress(1, 7)
    policy.record_study(progress, now=NOW)

    policy.record_answer(progress, correct=True, now=NOW)
    assert progress.status is VocabularyStatus.LEARNING
    assert progress.mastery_score == 0.5

    policy.record_answer(progress, correct=True, now=NOW + timedelta(minutes=1))
    assert progress.status is VocabularyStatus.MASTERED
    assert (progress.correct_count, progress.consecutive_correct) == (2, 2)
    assert progress.mastery_score == 1.0
    assert progress.next_review_at is None


def test_weak_item_recovers_through_two_consecutive_correct_answers() -> None:
    progress = new_progress(1, 7)
    policy.record_answer(progress, correct=True, now=NOW)
    policy.record_answer(progress, correct=False, now=NOW)  # streak broken → weak

    policy.record_answer(progress, correct=True, now=NOW)
    assert progress.status is VocabularyStatus.LEARNING
    assert progress.next_review_at is None

    policy.record_answer(progress, correct=True, now=NOW)
    assert progress.status is VocabularyStatus.MASTERED
    assert (progress.correct_count, progress.wrong_count) == (3, 1)


def test_mastery_streak_is_configurable() -> None:
    strict = SimpleProgressionPolicy(mastery_streak=3)
    progress = new_progress(1, 7)
    for _ in range(2):
        strict.record_answer(progress, correct=True, now=NOW)

    assert progress.status is VocabularyStatus.LEARNING
    strict.record_answer(progress, correct=True, now=NOW)
    assert progress.status is VocabularyStatus.MASTERED
