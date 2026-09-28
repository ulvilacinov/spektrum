"""Enforces that AI-extracted vocabulary really originates from the PDF.

Every item must have a German text and a Turkish meaning, and its ``source_text`` (or, if
missing, its ``german``) must occur on one of the pages it was extracted from. Items that
fail are rejected instead of stored. Matching tolerates case, whitespace and line wraps,
soft hyphens, typographic quotes/dashes, symbol-font bullets and words hyphenated across
line breaks. Because whitespace is ignored, very short single words match easily; the check
targets invented entries, which are almost always multi-word phrases or distinct words.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.db.models import VocabularyItem
from app.domain.entities import ExtractedPage
from app.services.ai.schemas import ExtractedVocabularyItem

_TYPOGRAPHY = str.maketrans(
    {"­": None, "’": "'", "‘": "'", "‚": "'", "„": '"', "“": '"', "”": '"', "–": "-", "—": "-"}
)
_LINE_BREAK_HYPHEN = re.compile(r"(\w)-[ \t]*\n\s*(\w)")
_WHITESPACE = re.compile(r"\s+")
_EDGE_PUNCTUATION = " \t\n,;:.!?()[]"


@dataclass(frozen=True, slots=True)
class RejectedItem:
    item: ExtractedVocabularyItem
    reason: str


@dataclass(slots=True)
class GroundingResult:
    accepted: list[ExtractedVocabularyItem] = field(default_factory=list)
    rejected: list[RejectedItem] = field(default_factory=list)


def ground_items(
    items: Sequence[ExtractedVocabularyItem], pages: Sequence[ExtractedPage]
) -> GroundingResult:
    page_variants = {page.page_number: _page_variants(page.text) for page in pages}
    result = GroundingResult()
    for item in items:
        grounded = _ground(item, page_variants)
        if isinstance(grounded, str):
            result.rejected.append(RejectedItem(item=item, reason=grounded))
        else:
            result.accepted.append(grounded)
    return result


def _ground(
    item: ExtractedVocabularyItem, page_variants: dict[int, tuple[str, str]]
) -> ExtractedVocabularyItem | str:
    """The grounded item, or the reason for rejecting it."""
    if reason := _missing_required(item):
        return reason
    source_text = item.source_text or item.german or ""
    page_number = _locate(_normalize(source_text), item.source_page, page_variants)
    if page_number is None:
        return "not found in the source pages"
    return _fit_to_columns(
        item.model_copy(update={"source_text": source_text, "source_page": page_number})
    )


def _missing_required(item: ExtractedVocabularyItem) -> str | None:
    if not item.german:
        return "missing German text"
    if not item.turkish:
        return "missing Turkish meaning"
    if len(item.german) > _max_length("german") or len(item.turkish) > _max_length("turkish"):
        return "text too long"
    return None


def _locate(
    needle: str, preferred_page: int | None, page_variants: dict[int, tuple[str, str]]
) -> int | None:
    if not needle:
        return None
    candidates = list(page_variants)
    if preferred_page in page_variants:
        candidates.remove(preferred_page)
        candidates.insert(0, preferred_page)
    for page_number in candidates:
        if any(needle in variant for variant in page_variants[page_number]):
            return page_number
    return None


def _page_variants(text: str) -> tuple[str, str]:
    """Page text with a real hyphen kept at line breaks ("Albrecht-Dürer-\\nHaus") and with
    line-break hyphenation joined ("Veran-\\nstaltung")."""
    text = unicodedata.normalize("NFKC", text).translate(_TYPOGRAPHY)
    return _normalize(text), _normalize(_LINE_BREAK_HYPHEN.sub(r"\1\2", text))


def _normalize(text: str) -> str:
    """Case-folded text without whitespace, so line wraps inside an entry never matter.

    PDF text breaks long entries anywhere ("Agentur\\u00ad\\nmeldungen", "sinkt/\\ngeht"), and
    the AI joins them, so spaces cannot be compared reliably.
    """
    text = unicodedata.normalize("NFKC", text).translate(_TYPOGRAPHY)
    # Private-use characters are symbol-font glyphs such as Wingdings bullets.
    text = "".join(char for char in text if unicodedata.category(char) != "Co")
    return _WHITESPACE.sub("", text.strip(_EDGE_PUNCTUATION)).casefold()


_OPTIONAL_SHORT_FIELDS = (
    "article",
    "base_verb",
    "prateritum",
    "perfekt",
    "preposition",
    "grammatical_case",
)


def _fit_to_columns(item: ExtractedVocabularyItem) -> ExtractedVocabularyItem:
    """Drop optional values that would not fit their database column."""
    too_long = {
        name: None
        for name in _OPTIONAL_SHORT_FIELDS
        if (value := getattr(item, name)) is not None and len(value) > _max_length(name)
    }
    return item.model_copy(update=too_long) if too_long else item


def _max_length(column: str) -> int:
    return VocabularyItem.__table__.c[column].type.length
