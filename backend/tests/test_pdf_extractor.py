from pathlib import Path

import pytest

from app.services.pdf import PdfExtractionError, PdfTextExtractor
from tests.pdf_factory import make_pdf

extractor = PdfTextExtractor()


def test_extracts_text_page_by_page_with_page_numbers() -> None:
    data = make_pdf(["Kapitel 1\ndie Veranstaltung", "an einer Konferenz teilnehmen", "Kapitel 2"])

    result = extractor.extract_pages(data)

    assert result.page_count == 3
    assert [page.page_number for page in result.pages] == [1, 2, 3]
    assert result.pages[0].text == "Kapitel 1\ndie Veranstaltung"
    assert result.pages[1].text == "an einer Konferenz teilnehmen"
    assert result.pages[2].text == "Kapitel 2"


def test_blank_pages_keep_their_page_number() -> None:
    result = extractor.extract_pages(make_pdf(["Kapitel 1", "", "Kapitel 2"]))

    assert [page.page_number for page in result.pages] == [1, 2, 3]
    assert result.pages[1].text == ""
    assert not result.pages[1].has_text
    assert result.pages[2].text == "Kapitel 2"


def test_preserves_german_characters() -> None:
    result = extractor.extract_pages(make_pdf(["die Größe, übermäßig, das Hörverständnis"]))

    assert result.pages[0].text == "die Größe, übermäßig, das Hörverständnis"


def test_extracts_from_file_path(tmp_path: Path) -> None:
    path = tmp_path / "vocab.pdf"
    path.write_bytes(make_pdf(["Kapitel 1", "Kapitel 2"]))

    result = extractor.extract_pages(path)

    assert [(p.page_number, p.text) for p in result.pages] == [(1, "Kapitel 1"), (2, "Kapitel 2")]


def test_validate_returns_page_count() -> None:
    assert extractor.validate(make_pdf(["a", "b", "c", "d"])) == 4


@pytest.mark.parametrize("data", [b"", b"not a pdf", b"%PDF-1.7 corrupted body"])
def test_rejects_unreadable_data(data: bytes) -> None:
    with pytest.raises(PdfExtractionError) as exc_info:
        extractor.extract_pages(data)
    assert exc_info.value.code == "invalid_pdf"


def test_rejects_password_protected_pdf() -> None:
    with pytest.raises(PdfExtractionError, match="Password-protected"):
        extractor.validate(make_pdf(["geheim"], password="secret"))
