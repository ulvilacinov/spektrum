from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import LearningSession, QuizQuestion
from app.domain.enums import (
    ErrorType,
    EvaluationMethod,
    QuestionType,
    SessionMode,
    VocabularyStatus,
)
from app.schemas.vocabulary import VocabularyItemRead
from app.services.learning import AnswerOutcome, Quiz, SessionItem

DEFAULT_BATCH_SIZE = 10
MAX_BATCH_SIZE = 100


class LearningSessionCreate(BaseModel):
    chapter_id: int
    batch_size: int = Field(
        default=DEFAULT_BATCH_SIZE,
        ge=1,
        le=MAX_BATCH_SIZE,
        description="Number of words to study (e.g. 5, 10 or 20).",
    )
    mode: SessionMode = Field(
        default=SessionMode.NEW,
        description="new: the chapter's next unstudied words (once the batch is unlocked); "
        "review: studied but not yet mastered words, weak ones first.",
    )


class LearningSessionRead(BaseModel):
    id: int
    chapter_id: int
    batch_size: int
    mode: SessionMode
    item_count: int = Field(description="Can be below batch_size for the chapter's last batch.")
    started_at: datetime
    completed_at: datetime | None
    correct_count: int
    wrong_count: int

    @classmethod
    def from_session(cls, learning_session: LearningSession) -> Self:
        return cls(
            id=learning_session.id,
            chapter_id=learning_session.chapter_id,
            batch_size=learning_session.batch_size,
            mode=learning_session.mode,
            item_count=len(learning_session.items),
            started_at=learning_session.started_at,
            completed_at=learning_session.completed_at,
            correct_count=learning_session.correct_count,
            wrong_count=learning_session.wrong_count,
        )


class LearningSessionItemRead(BaseModel):
    position: int
    status: VocabularyStatus
    vocabulary_item: VocabularyItemRead

    @classmethod
    def from_item(cls, item: SessionItem) -> Self:
        return cls(
            position=item.position,
            status=item.progress.status if item.progress else VocabularyStatus.NEW,
            vocabulary_item=VocabularyItemRead.model_validate(item.vocabulary_item),
        )


class QuizQuestionRead(BaseModel):
    """A question as shown to the learner. Answer fields stay empty until it is answered."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    vocabulary_item_id: int
    question_type: QuestionType
    question: str
    user_answer: str | None
    is_correct: bool | None
    score: float | None
    expected_answer: str | None = Field(description="Revealed only after answering.")
    corrected_answer: str | None
    ai_feedback: str | None = Field(description="Turkish explanation of the evaluation.")
    error_type: ErrorType | None
    evaluation_method: EvaluationMethod | None
    answered_at: datetime | None

    @classmethod
    def from_question(cls, question: QuizQuestion) -> Self:
        read = cls.model_validate(question)
        if question.user_answer is None:
            read.expected_answer = None
        return read


class QuizRead(BaseModel):
    learning_session_id: int
    question_count: int
    questions: list[QuizQuestionRead]

    @classmethod
    def from_quiz(cls, quiz: Quiz) -> Self:
        questions = [QuizQuestionRead.from_question(question) for question in quiz.questions]
        return cls(
            learning_session_id=quiz.learning_session.id,
            question_count=len(questions),
            questions=questions,
        )


class AnswerSubmit(BaseModel):
    answer: str = Field(min_length=1, max_length=1000)

    @field_validator("answer")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("The answer must not be empty.")
        return value


class AnswerResultRead(BaseModel):
    question: QuizQuestionRead
    vocabulary_status: VocabularyStatus
    learning_session: LearningSessionRead

    @classmethod
    def from_outcome(cls, outcome: AnswerOutcome) -> Self:
        return cls(
            question=QuizQuestionRead.from_question(outcome.question),
            vocabulary_status=outcome.progress.status,
            learning_session=LearningSessionRead.from_session(outcome.learning_session),
        )
