from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, enum_column
from app.domain.enums import ErrorType, EvaluationMethod, QuestionType


class QuizQuestion(Base):
    """One quiz question about one vocabulary item of a learning session."""

    __tablename__ = "quiz_questions"
    __table_args__ = (UniqueConstraint("learning_session_id", "position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Indexed by the (learning_session_id, position) unique constraint.
    learning_session_id: Mapped[int] = mapped_column(
        ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False
    )
    vocabulary_item_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    question_type: Mapped[QuestionType] = mapped_column(
        enum_column(QuestionType, length=32), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)

    user_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Turkish explanation for the learner (from the AI or a rule template).
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    corrected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_type: Mapped[ErrorType | None] = mapped_column(
        enum_column(ErrorType, length=32), nullable=True
    )
    evaluation_method: Mapped[EvaluationMethod | None] = mapped_column(
        enum_column(EvaluationMethod, length=20), nullable=True
    )
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<QuizQuestion id={self.id} session={self.learning_session_id} "
            f"type={self.question_type}>"
        )
