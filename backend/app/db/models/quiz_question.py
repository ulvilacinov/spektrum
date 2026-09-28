from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, enum_column
from app.domain.enums import QuestionType


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
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<QuizQuestion id={self.id} session={self.learning_session_id} "
            f"type={self.question_type}>"
        )
