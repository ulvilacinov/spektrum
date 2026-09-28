from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import LearningSession
from app.domain.enums import QuestionType, VocabularyStatus
from app.schemas.vocabulary import VocabularyItemRead
from app.services.learning import Quiz, SessionItem

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


class LearningSessionRead(BaseModel):
    id: int
    chapter_id: int
    batch_size: int
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
    """A question as shown to the learner. The expected answer stays hidden."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    vocabulary_item_id: int
    question_type: QuestionType
    question: str
    user_answer: str | None
    is_correct: bool | None
    ai_feedback: str | None


class QuizRead(BaseModel):
    learning_session_id: int
    question_count: int
    questions: list[QuizQuestionRead]

    @classmethod
    def from_quiz(cls, quiz: Quiz) -> Self:
        questions = [QuizQuestionRead.model_validate(question) for question in quiz.questions]
        return cls(
            learning_session_id=quiz.learning_session.id,
            question_count=len(questions),
            questions=questions,
        )
