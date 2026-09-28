import io
from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.services.documents import DocumentService, LocalFileStorage
from app.services.pdf import PdfTextExtractor
from tests.pdf_factory import make_pdf


@pytest.fixture
def service(sqlite_session: Session, upload_dir: Path) -> DocumentService:
    return DocumentService(
        sqlite_session,
        storage=LocalFileStorage(upload_dir),
        extractor=PdfTextExtractor(),
        max_upload_bytes=1024 * 1024,
    )


def upload(service: DocumentService, data: bytes):
    return service.upload(
        file=io.BytesIO(data), filename="vocab.pdf", content_type="application/pdf"
    )


def test_extract_pages_of_stored_document(service: DocumentService) -> None:
    document = upload(service, make_pdf(["Kapitel 1\ndie Veranstaltung", "", "Kapitel 2"]))

    result = service.extract_pages(document.id)

    assert [(p.page_number, p.text) for p in result.pages] == [
        (1, "Kapitel 1\ndie Veranstaltung"),
        (2, ""),
        (3, "Kapitel 2"),
    ]


def test_extract_pages_reports_missing_file(service: DocumentService, upload_dir: Path) -> None:
    document = upload(service, make_pdf(["Kapitel 1"]))
    (upload_dir / document.storage_path).unlink()

    with pytest.raises(NotFoundError) as exc_info:
        service.extract_pages(document.id)
    assert exc_info.value.code == "document_file_missing"


def test_extract_pages_of_unknown_document(service: DocumentService) -> None:
    with pytest.raises(NotFoundError):
        service.extract_pages(123)


def test_failed_commit_removes_the_stored_file(
    service: DocumentService, sqlite_session: Session, upload_dir: Path, monkeypatch
) -> None:
    def broken_commit() -> None:
        raise OperationalError("COMMIT", {}, Exception("connection lost"))

    monkeypatch.setattr(sqlite_session, "commit", broken_commit)

    with pytest.raises(OperationalError):
        upload(service, make_pdf(["Kapitel 1"]))
    assert list(upload_dir.iterdir()) == []


@pytest.mark.parametrize("key", ["../outside.pdf", "/etc/passwd", "a/../../b.pdf", ""])
def test_storage_rejects_keys_outside_the_root(upload_dir: Path, key: str) -> None:
    with pytest.raises(ValueError):
        LocalFileStorage(upload_dir).resolve(key)
