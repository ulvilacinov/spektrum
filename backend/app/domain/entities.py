from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    """Plain text of one PDF page. ``page_number`` is 1-based, as printed in the PDF viewer."""

    page_number: int
    text: str

    @property
    def has_text(self) -> bool:
        return bool(self.text)


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    pages: tuple[ExtractedPage, ...]

    @property
    def page_count(self) -> int:
        return len(self.pages)
