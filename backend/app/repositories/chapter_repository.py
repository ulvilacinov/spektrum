from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import Chapter, Document, VocabularyItem


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

    def get(self, chapter_id: int, *, user_id: int | None = None) -> Chapter | None:
        """The chapter; with ``user_id`` only if that user owns its document."""
        chapter = self.session.get(Chapter, chapter_id)
        if chapter is None or (user_id is not None and chapter.document.user_id != user_id):
            return None
        return chapter

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

    def list_chapters(self, *, user_id: int, document_id: int | None = None) -> Sequence[Chapter]:
        """The user's chapters (of one document or all), in reading order."""
        statement = (
            select(Chapter)
            .join(Document, Document.id == Chapter.document_id)
            .where(Document.user_id == user_id)
            .order_by(Chapter.document_id, Chapter.order)
        )
        if document_id is not None:
            statement = statement.where(Chapter.document_id == document_id)
        return self.session.scalars(statement).all()
