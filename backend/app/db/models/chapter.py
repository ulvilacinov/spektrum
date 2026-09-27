from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.document import Document
    from app.db.models.vocabulary_item import VocabularyItem


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (
        UniqueConstraint("document_id", "order"),
        CheckConstraint("source_start_page >= 1", name="start_page_positive"),
        CheckConstraint("source_end_page >= source_start_page", name="page_range_valid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # Nullable: some PDFs contain unnumbered sections (e.g. "Einleitung", "Wortschatz extra").
    chapter_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    source_start_page: Mapped[int] = mapped_column(Integer, nullable=False)
    source_end_page: Mapped[int] = mapped_column(Integer, nullable=False)

    document: Mapped[Document] = relationship(back_populates="chapters")
    vocabulary_items: Mapped[list[VocabularyItem]] = relationship(
        back_populates="chapter",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="VocabularyItem.order",
    )

    def __repr__(self) -> str:
        return f"<Chapter id={self.id} title={self.title!r} order={self.order}>"
