import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pymupdf

from app.core.exceptions import UnprocessableError
from app.domain.entities import ExtractedDocument, ExtractedPage

_EXCESS_BLANK_LINES = re.compile(r"\n{3,}")


class PdfExtractionError(UnprocessableError):
    code = "invalid_pdf"


class PdfTextExtractor:
    """Reads PDFs with PyMuPDF. Knows nothing about the database or HTTP."""

    def validate(self, data: bytes) -> int:
        """Ensure ``data`` is a readable, unencrypted PDF with pages; return its page count."""
        with self._open(data) as document:
            return document.page_count

    def extract_pages(self, source: Path | bytes) -> ExtractedDocument:
        """Extract text page by page, keeping the 1-based page number of every page.

        Pages without a text layer (e.g. scanned images) are kept with empty text so that
        page numbers always match the original PDF.
        """
        with self._open(source) as document:
            pages = tuple(
                ExtractedPage(page_number=index + 1, text=_normalize(page.get_text("text")))
                for index, page in enumerate(document)
            )
        return ExtractedDocument(pages=pages)

    @contextmanager
    def _open(self, source: Path | bytes) -> Iterator[pymupdf.Document]:
        try:
            if isinstance(source, Path):
                document = pymupdf.open(source, filetype="pdf")
            else:
                document = pymupdf.open(stream=source, filetype="pdf")
        except (RuntimeError, ValueError) as exc:  # pymupdf.FileDataError is a RuntimeError
            raise PdfExtractionError("The file is not a readable PDF.") from exc

        try:
            if document.needs_pass:
                raise PdfExtractionError("Password-protected PDFs are not supported.")
            if document.page_count == 0:
                raise PdfExtractionError("The PDF has no pages.")
            yield document
        finally:
            document.close()


def _normalize(text: str) -> str:
    """Unify line endings, drop trailing spaces and collapse runs of blank lines."""
    lines = (line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
    return _EXCESS_BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()
