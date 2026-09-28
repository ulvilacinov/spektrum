"""Answer evaluation: exact match → normalized comparison → rule or AI, then progression."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.db.models import LearningSession, QuizQuestion, UserVocabularyProgress, VocabularyItem
from app.domain.enums import ErrorType, EvaluationMethod, QuestionType
from app.repositories.learning_repository import LearningRepository
from app.services.ai.provider import AIProvider
from app.services.ai.schemas import AnswerEvaluationRequest
from app.services.learning.answer_matching import Language, match_answer
from app.services.learning.progression import ProgressionPolicy, new_progress

# Questions with one short, closed answer: judged without AI.
_RULE_FEEDBACK: dict[QuestionType, tuple[ErrorType, str]] = {
    QuestionType.ARTICLE: (ErrorType.ARTICLE, "Doğru artikel „{expected}“: {german}."),
    QuestionType.PREPOSITION: (ErrorType.PREPOSITION, "Doğru edat „{expected}“: {german}."),
    QuestionType.VERB_CONJUGATION: (
        ErrorType.VERB_CONJUGATION,
        "Doğru biçim: „{expected}“ ({german}).",
    ),
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Evaluation:
    is_correct: bool
    score: float
    explanation: str
    corrected_answer: str
    error_type: ErrorType | None
    method: EvaluationMethod


@dataclass(frozen=True, slots=True)
class AnswerOutcome:
    question: QuizQuestion
    progress: UserVocabularyProgress
    learning_session: LearningSession


class AnswerService:
    def __init__(
        self,
        session: Session,
        *,
        policy: ProgressionPolicy,
        ai_provider_factory: Callable[[], AIProvider],
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.session = session
        self.learning = LearningRepository(session)
        self.policy = policy
        # Created only when a question actually needs AI, so deterministic answers work
        # without an AI configuration.
        self.ai_provider_factory = ai_provider_factory
        self.clock = clock

    def submit(self, *, user_id: int, question_id: int, answer: str) -> AnswerOutcome:
        found = self.learning.question_with_context(question_id)
        if found is None or found[1].user_id != user_id:
            raise NotFoundError(
                f"Quiz question {question_id} was not found.",
                details={"question_id": question_id},
            )
        question, learning_session, item = found
        if question.user_answer is not None:
            raise self._already_answered(question_id)

        # May call the AI; nothing is written before the evaluation succeeded, so a failed
        # AI call leaves the question unanswered and the learner can simply retry.
        evaluation = self.evaluate(question, item, answer)

        now = self.clock()
        recorded = self.learning.record_answer(
            question_id,
            user_answer=answer,
            is_correct=evaluation.is_correct,
            score=evaluation.score,
            corrected_answer=evaluation.corrected_answer,
            ai_feedback=evaluation.explanation,
            error_type=evaluation.error_type,
            evaluation_method=evaluation.method,
            answered_at=now,
        )
        if not recorded:  # a concurrent request answered it first
            self.session.rollback()
            raise self._already_answered(question_id)

        progress = self.learning.progress_by_item(
            user_id=user_id, vocabulary_item_ids=[item.id]
        ).get(item.id)
        if progress is None:
            progress = new_progress(user_id, item.id)
            self.learning.add(progress)
        self.policy.record_answer(progress, correct=evaluation.is_correct, now=now)

        if evaluation.is_correct:
            learning_session.correct_count += 1
        else:
            learning_session.wrong_count += 1
        self.session.flush()
        if self.learning.unanswered_question_count(learning_session.id) == 0:
            learning_session.completed_at = now

        self.session.commit()
        self.session.refresh(question)
        return AnswerOutcome(
            question=question, progress=progress, learning_session=learning_session
        )

    def evaluate(self, question: QuizQuestion, item: VocabularyItem, answer: str) -> Evaluation:
        expected = question.expected_answer
        language = (
            Language.TURKISH
            if question.question_type is QuestionType.GERMAN_TO_TURKISH
            else Language.GERMAN
        )
        method = match_answer(answer, expected, language)
        if method is not None:
            explanation = (
                "Doğru!"
                if method is EvaluationMethod.EXACT
                else f"Doğru! Kitaptaki yazılışı: „{expected}“."
            )
            return Evaluation(True, 1.0, explanation, expected, None, method)

        if question.question_type in _RULE_FEEDBACK:
            error_type, template = _RULE_FEEDBACK[question.question_type]
            explanation = "Yanlış. " + template.format(expected=expected, german=item.german)
            return Evaluation(False, 0.0, explanation, expected, error_type, EvaluationMethod.RULE)

        result = self.ai_provider_factory().evaluate_answer(
            AnswerEvaluationRequest(
                question_type=question.question_type,
                question=question.question,
                expected_answer=expected,
                user_answer=answer,
                answer_language="Turkish" if language is Language.TURKISH else "German",
                german=item.german,
                turkish=item.turkish,
            )
        )
        return Evaluation(
            is_correct=result.is_correct,
            score=result.score,
            explanation=result.explanation,
            corrected_answer=result.corrected_answer or expected,
            error_type=None if result.is_correct else (result.error_type or ErrorType.MEANING),
            method=EvaluationMethod.AI,
        )

    @staticmethod
    def _already_answered(question_id: int) -> ConflictError:
        return ConflictError(
            "This question has already been answered.",
            code="question_already_answered",
            details={"question_id": question_id},
        )
