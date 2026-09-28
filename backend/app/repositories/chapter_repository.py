from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import Chapter, VocabularyItem


class ChapterRepository:
    """Database access for chapters and their vocabulary. Never commits."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def replace_for_document(self, document_id: int, chapters: Sequence[Chapter]) -> None:
        """Delete a document's chapters (and their vocabulary) and store ``chapters`` instead.

        Old rows are deleted and flushed first so the new ones cannot collide with the
        (document_id, order) unique constraint.
        """
        chapter_ids = select(Chapter.id).where(Chapter.document_id == document_id)
        self.session.execute(
            delete(VocabularyItem).where(VocabularyItem.chapter_id.in_(chapter_ids))
        )
        self.session.execute(delete(Chapter).where(Chapter.document_id == document_id))
        self.session.flush()
        for chapter in chapters:
            chapter.document_id = document_id
        self.session.add_all(chapters)
        self.session.flush()

    def get(self, chapter_id: int) -> Chapter | None:
        return self.session.get(Chapter, chapter_id)

    def list_with_vocabulary_counts(self, document_id: int) -> list[tuple[Chapter, int]]:
        """A document's chapters in reading order, each with its number of vocabulary items."""
        vocabulary_count = func.count(VocabularyItem.id)
        statement = (
            select(Chapter, vocabulary_count)
            .outerjoin(VocabularyItem, VocabularyItem.chapter_id == Chapter.id)
            .where(Chapter.document_id == document_id)
            .group_by(Chapter.id)
            .order_by(Chapter.order)
        )
        return [(chapter, count) for chapter, count in self.session.execute(statement)]

    def list_vocabulary(self, chapter_id: int) -> Sequence[VocabularyItem]:
        statement = (
            select(VocabularyItem)
            .where(VocabularyItem.chapter_id == chapter_id)
            .order_by(VocabularyItem.order)
        )
        return self.session.scalars(statement).all()
