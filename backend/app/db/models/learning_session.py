from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, enum_column
from app.domain.enums import SessionMode

if TYPE_CHECKING:
    from app.db.models.chapter import Chapter
    from app.db.models.vocabulary_item import VocabularyItem


class LearningSession(Base):
    """One study batch (e.g. 10 words) of a chapter, later followed by its quiz."""

    __tablename__ = "learning_sessions"
    __table_args__ = (CheckConstraint("batch_size > 0", name="batch_size_positive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[SessionMode] = mapped_column(
        enum_column(SessionMode, length=20),
        nullable=False,
        default=SessionMode.NEW,
        server_default=SessionMode.NEW.value,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    correct_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    chapter: Mapped[Chapter] = relationship()
    items: Mapped[list[LearningSessionItem]] = relationship(
        back_populates="learning_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="LearningSessionItem.position",
    )

    def __repr__(self) -> str:
        return f"<LearningSession id={self.id} chapter={self.chapter_id} size={self.batch_size}>"


class LearningSessionItem(Base):
    """Which vocabulary items a session studies, in display order."""

    __tablename__ = "learning_session_items"
    __table_args__ = (
        UniqueConstraint("learning_session_id", "position"),
        # Explicit name: the generated one would exceed PostgreSQL's 63-character limit.
        UniqueConstraint(
            "learning_session_id", "vocabulary_item_id", name="uq_learning_session_items_item"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Indexed by the (learning_session_id, position) unique constraint.
    learning_session_id: Mapped[int] = mapped_column(
        ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False
    )
    vocabulary_item_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    learning_session: Mapped[LearningSession] = relationship(back_populates="items")
    vocabulary_item: Mapped[VocabularyItem] = relationship()
