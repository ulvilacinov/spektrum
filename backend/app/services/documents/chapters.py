from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models import Chapter, VocabularyItem
from app.repositories.chapter_repository import ChapterRepository
from app.repositories.document_repository import DocumentRepository


class ChapterService:
    """Read access to the chapters and vocabulary stored by the document analysis."""

    def __init__(self, session: Session) -> None:
        self.documents = DocumentRepository(session)
        self.chapters = ChapterRepository(session)

    def list_for_document(self, document_id: int) -> list[tuple[Chapter, int]]:
        """Chapters with their vocabulary counts; empty until the document is analyzed."""
        if self.documents.get(document_id) is None:
            raise NotFoundError(
                f"Document {document_id} was not found.", details={"document_id": document_id}
            )
        return self.chapters.list_with_vocabulary_counts(document_id)

    def list_vocabulary(self, chapter_id: int) -> Sequence[VocabularyItem]:
        if self.chapters.get(chapter_id) is None:
            raise NotFoundError(
                f"Chapter {chapter_id} was not found.", details={"chapter_id": chapter_id}
            )
        return self.chapters.list_vocabulary(chapter_id)
