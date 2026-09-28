from collections.abc import Collection, Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import Document
from app.domain.enums import DocumentStatus


class DocumentRepository:
    """Database access for documents. Never commits; the calling service owns the transaction."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, document: Document) -> Document:
        self.session.add(document)
        self.session.flush()
        return document

    def get(self, document_id: int) -> Document | None:
        return self.session.get(Document, document_id)

    def list(self, *, limit: int, offset: int) -> Sequence[Document]:
        statement = (
            select(Document)
            .order_by(Document.uploaded_at.desc(), Document.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return self.session.scalars(statement).all()

    def transition_status(
        self,
        document_id: int,
        *,
        from_statuses: Collection[DocumentStatus],
        to_status: DocumentStatus,
    ) -> bool:
        """Atomically change the status if it is currently one of ``from_statuses``.

        A single conditional UPDATE, so two concurrent requests cannot both win.
        """
        result = self.session.execute(
            update(Document)
            .where(Document.id == document_id, Document.status.in_(from_statuses))
            .values(status=to_status, error_message=None)
        )
        return result.rowcount == 1
