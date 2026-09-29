import uuid
from collections.abc import Sequence
from pathlib import PureWindowsPath
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core.exceptions import (
    NotFoundError,
    PayloadTooLargeError,
    UnprocessableError,
    UnsupportedMediaTypeError,
)
from app.db.models import Document
from app.domain.entities import ExtractedDocument
from app.domain.enums import DocumentStatus
from app.repositories.document_repository import DocumentRepository
from app.services.documents.storage import LocalFileStorage
from app.services.pdf.extractor import PdfExtractionError, PdfTextExtractor

PDF_EXTENSION = ".pdf"
PDF_SIGNATURE = b"%PDF-"
# Some clients (curl without a type, a few OS file pickers) label PDFs as octet-stream;
# the signature and PyMuPDF checks below are the real validation.
ALLOWED_CONTENT_TYPES = frozenset(
    {"application/pdf", "application/x-pdf", "application/octet-stream"}
)
MAX_FILE_NAME_LENGTH = 255


class DocumentService:
    def __init__(
        self,
        session: Session,
        *,
        storage: LocalFileStorage,
        extractor: PdfTextExtractor,
        max_upload_bytes: int,
    ) -> None:
        self.session = session
        self.documents = DocumentRepository(session)
        self.storage = storage
        self.extractor = extractor
        self.max_upload_bytes = max_upload_bytes

    def upload(
        self,
        *,
        file: BinaryIO,
        filename: str | None,
        content_type: str | None,
        user_id: int,
    ) -> Document:
        """Validate an uploaded PDF, store it on disk and register it as a Document."""
        original_file_name = self._validate_file_name(filename)
        self._validate_content_type(content_type)
        data = self._read_limited(file)
        self._validate_pdf(data)

        file_name = f"{uuid.uuid4().hex}{PDF_EXTENSION}"
        self.storage.save(file_name, data)
        try:
            document = self.documents.add(
                Document(
                    user_id=user_id,
                    file_name=file_name,
                    original_file_name=original_file_name,
                    storage_path=file_name,
                    status=DocumentStatus.UPLOADED,
                )
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            self.storage.delete(file_name)
            raise
        self.session.refresh(document)  # load server-generated uploaded_at
        return document

    def list_documents(self, *, user_id: int, limit: int, offset: int) -> Sequence[Document]:
        return self.documents.list(user_id=user_id, limit=limit, offset=offset)

    def get_document(self, document_id: int, *, user_id: int | None = None) -> Document:
        """The document; with ``user_id`` a document of another user is "not found"."""
        document = self.documents.get(document_id, user_id=user_id)
        if document is None:
            raise NotFoundError(
                f"Document {document_id} was not found.", details={"document_id": document_id}
            )
        return document

    def extract_pages(self, document_id: int) -> ExtractedDocument:
        """Page-by-page text of a stored document; the input for chapter detection."""
        document = self.get_document(document_id)
        path = self.storage.resolve(document.storage_path)
        if not path.is_file():
            raise NotFoundError(
                f"The file of document {document_id} is missing from storage.",
                code="document_file_missing",
                details={"document_id": document_id},
            )
        return self.extractor.extract_pages(path)

    @staticmethod
    def _validate_file_name(filename: str | None) -> str:
        # Some browsers send a full client path; keep only the last component.
        name = PureWindowsPath(filename or "").name.strip()
        if not name:
            raise UnprocessableError("The uploaded file has no name.", code="missing_file_name")
        if not name.lower().endswith(PDF_EXTENSION):
            raise UnsupportedMediaTypeError(
                "Only PDF files are accepted.", details={"file_name": name}
            )
        if len(name) > MAX_FILE_NAME_LENGTH:
            stem = name[: MAX_FILE_NAME_LENGTH - len(PDF_EXTENSION)]
            name = f"{stem}{PDF_EXTENSION}"
        return name

    @staticmethod
    def _validate_content_type(content_type: str | None) -> None:
        if content_type is None:
            return
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type not in ALLOWED_CONTENT_TYPES:
            raise UnsupportedMediaTypeError(
                "Only PDF files are accepted.", details={"content_type": media_type}
            )

    def _read_limited(self, file: BinaryIO) -> bytes:
        # Read one byte past the limit so oversized files are detected without reading them fully.
        data = file.read(self.max_upload_bytes + 1)
        if len(data) > self.max_upload_bytes:
            raise PayloadTooLargeError(
                "The file exceeds the maximum upload size.",
                details={"max_bytes": self.max_upload_bytes},
            )
        if not data:
            raise UnprocessableError("The uploaded file is empty.", code="empty_file")
        return data

    def _validate_pdf(self, data: bytes) -> None:
        if not data.startswith(PDF_SIGNATURE):
            raise PdfExtractionError("The file content is not a PDF.")
        self.extractor.validate(data)
