from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, enum_column
from app.domain.enums import VocabularyStatus


class UserVocabularyProgress(Base):
    """One user's learning state for one vocabulary item. Changed only by ProgressionPolicy."""

    __tablename__ = "user_vocabulary_progress"
    __table_args__ = (UniqueConstraint("user_id", "vocabulary_item_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # No users table in the MVP yet; becomes a foreign key once authentication exists.
    # Indexed by the (user_id, vocabulary_item_id) unique constraint.
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    vocabulary_item_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary_items.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[VocabularyStatus] = mapped_column(
        enum_column(VocabularyStatus, length=20),
        nullable=False,
        default=VocabularyStatus.NEW,
        server_default=VocabularyStatus.NEW.value,
    )

    seen_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    correct_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    consecutive_correct: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # 0.0 (unknown) … 1.0 (mastered); the policy decides how it is computed.
    mastery_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default="0"
    )

    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<UserVocabularyProgress user={self.user_id} item={self.vocabulary_item_id} "
            f"status={self.status}>"
        )
