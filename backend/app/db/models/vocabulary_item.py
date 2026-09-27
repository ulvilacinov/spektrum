from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, enum_column
from app.domain.enums import VocabularyItemType

if TYPE_CHECKING:
    from app.db.models.chapter import Chapter


class VocabularyItem(Base):
    __tablename__ = "vocabulary_items"
    __table_args__ = (UniqueConstraint("chapter_id", "order"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True
    )

    german: Mapped[str] = mapped_column(String(500), nullable=False)
    turkish: Mapped[str] = mapped_column(String(500), nullable=False)

    item_type: Mapped[VocabularyItemType] = mapped_column(
        enum_column(VocabularyItemType, length=32), nullable=False
    )
    # Free strings rather than enums: PDFs contain values like "die (Pl.)" or "Akkusativ/Dativ".
    article: Mapped[str | None] = mapped_column(String(20), nullable=True)

    base_verb: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prateritum: Mapped[str | None] = mapped_column(String(255), nullable=True)
    perfekt: Mapped[str | None] = mapped_column(String(255), nullable=True)

    preposition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grammatical_case: Mapped[str | None] = mapped_column(String(50), nullable=True)

    example_german: Mapped[str | None] = mapped_column(Text, nullable=True)
    example_turkish: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    order: Mapped[int] = mapped_column(Integer, nullable=False)

    chapter: Mapped[Chapter] = relationship(back_populates="vocabulary_items")

    def __repr__(self) -> str:
        return f"<VocabularyItem id={self.id} german={self.german!r} type={self.item_type}>"
