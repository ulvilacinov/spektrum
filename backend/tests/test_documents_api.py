from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document
from app.domain.enums import DocumentStatus
from tests.pdf_factory import make_pdf

ONE_MB = 1024 * 1024  # the test settings limit uploads to 1 MB


def upload(
    client: TestClient,
    data: bytes,
    name: str = "Wortschatz B1.pdf",
    content_type: str = "application/pdf",
):
    return client.post("/api/documents", files={"file": (name, data, content_type)})


def stored_files(upload_dir: Path) -> list[Path]:
    return [path for path in upload_dir.iterdir() if path.is_file()]


def test_upload_stores_file_and_creates_document(
    client: TestClient, sqlite_session: Session, upload_dir: Path
) -> None:
    data = make_pdf(["Kapitel 1", "die Veranstaltung"])

    response = upload(client, data)

    assert response.status_code == 201
    body = response.json()
    assert body["original_file_name"] == "Wortschatz B1.pdf"
    assert body["status"] == "uploaded"
    assert body["file_name"].endswith(".pdf")
    assert body["file_name"] != "Wortschatz B1.pdf"
    assert body["uploaded_at"] is not None
    assert body["processed_at"] is None
    assert body["error_message"] is None
    assert "storage_path" not in body

    document = sqlite_session.scalars(select(Document)).one()
    assert document.id == body["id"]
    assert document.status is DocumentStatus.UPLOADED
    assert document.storage_path == body["file_name"]
    assert (upload_dir / document.storage_path).read_bytes() == data


def test_upload_keeps_only_the_base_name_of_client_paths(client: TestClient) -> None:
    response = upload(client, make_pdf(["x"]), name="C:\\Users\\me\\Kapitel.PDF")

    assert response.status_code == 201
    assert response.json()["original_file_name"] == "Kapitel.PDF"


def test_upload_accepts_octet_stream_when_content_is_pdf(client: TestClient) -> None:
    response = upload(client, make_pdf(["x"]), content_type="application/octet-stream")

    assert response.status_code == 201


@pytest.mark.parametrize(
    ("name", "content_type"),
    [
        ("notes.txt", "application/pdf"),
        ("vocab.pdf", "text/plain"),
        ("vocab.docx", "application/octet-stream"),
    ],
)
def test_upload_rejects_non_pdf_type(
    client: TestClient, upload_dir: Path, name: str, content_type: str
) -> None:
    response = upload(client, make_pdf(["x"]), name=name, content_type=content_type)

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"
    assert stored_files(upload_dir) == []


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"", "empty_file"),
        (b"PK\x03\x04 this is a zip file", "invalid_pdf"),
        (b"%PDF-1.7 truncated garbage", "invalid_pdf"),
        (make_pdf(["geheim"], password="secret"), "invalid_pdf"),
    ],
)
def test_upload_rejects_invalid_content(
    client: TestClient, sqlite_session: Session, upload_dir: Path, data: bytes, code: str
) -> None:
    response = upload(client, data)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    assert stored_files(upload_dir) == []
    assert sqlite_session.scalars(select(Document)).all() == []


def test_upload_rejects_files_over_the_size_limit(client: TestClient, upload_dir: Path) -> None:
    response = upload(client, b"%PDF-" + b"0" * ONE_MB)

    assert response.status_code == 413
    assert response.json()["error"] == {
        "code": "payload_too_large",
        "message": "The file exceeds the maximum upload size.",
        "details": {"max_bytes": ONE_MB},
    }
    assert stored_files(upload_dir) == []


def test_upload_without_file_is_a_validation_error(client: TestClient) -> None:
    assert client.post("/api/documents").status_code == 422


def test_list_documents_newest_first_with_pagination(client: TestClient) -> None:
    ids = [
        upload(client, make_pdf([f"Kapitel {n}"]), name=f"v{n}.pdf").json()["id"] for n in range(3)
    ]

    listed = client.get("/api/documents")
    assert listed.status_code == 200
    assert [d["id"] for d in listed.json()] == list(reversed(ids))

    page = client.get("/api/documents", params={"limit": 1, "offset": 1})
    assert [d["id"] for d in page.json()] == [ids[1]]


def test_list_documents_empty(client: TestClient) -> None:
    assert client.get("/api/documents").json() == []


def test_list_documents_validates_limit(client: TestClient) -> None:
    assert client.get("/api/documents", params={"limit": 0}).status_code == 422
    assert client.get("/api/documents", params={"limit": 101}).status_code == 422


def test_get_document(client: TestClient) -> None:
    created = upload(client, make_pdf(["Kapitel 1"])).json()

    response = client.get(f"/api/documents/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_document_returns_404(client: TestClient) -> None:
    response = client.get("/api/documents/999")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Document 999 was not found.",
            "details": {"document_id": 999},
        }
    }
