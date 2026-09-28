"""Structured output contract between the application and any AI provider.

The models are deliberately lenient (blank strings become ``None``, unknown item types fall
back to ``word``) so that one sloppy field does not discard a whole response. Business rules,
such as "every item must originate from the PDF", are enforced afterwards by the services.
"""

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field

from app.domain.enums import VocabularyItemType


def _blank_to_none(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


_ITEM_TYPES = frozenset(member.value for member in VocabularyItemType)


def _item_type(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip().lower()
        return value if value in _ITEM_TYPES else VocabularyItemType.WORD.value
    return value


OptionalText = Annotated[str | None, BeforeValidator(_blank_to_none)]


class DetectedChapter(BaseModel):
    title: str = Field(description="Chapter heading exactly as printed, e.g. 'Kapitel 1'.")
    chapter_number: int | None = Field(
        default=None, description="Number of the chapter, null for unnumbered sections."
    )
    start_page: int = Field(description="Page marker number where the chapter starts.")
    starts_mid_page: bool = Field(
        default=False,
        description="True only if the chapter begins in the middle of its start page, "
        "after content that still belongs to the previous chapter.",
    )


class ChapterDetectionResult(BaseModel):
    chapters: list[DetectedChapter] = Field(default_factory=list)


class ExtractedVocabularyItem(BaseModel):
    german: OptionalText = Field(description="German word or phrase in dictionary form.")
    turkish: OptionalText = Field(description="Turkish meaning.")
    item_type: Annotated[VocabularyItemType, BeforeValidator(_item_type)] = VocabularyItemType.WORD
    article: OptionalText = None
    base_verb: OptionalText = None
    prateritum: OptionalText = None
    perfekt: OptionalText = None
    preposition: OptionalText = None
    grammatical_case: OptionalText = None
    example_german: OptionalText = None
    example_turkish: OptionalText = None
    source_text: OptionalText = Field(
        default=None, description="The item's text copied verbatim from the page."
    )
    source_page: int | None = Field(default=None, description="Page the item appears on.")


class VocabularySection(BaseModel):
    name: OptionalText = None
    items: list[ExtractedVocabularyItem] = Field(default_factory=list)


class VocabularyExtractionResult(BaseModel):
    chapter_title: OptionalText = None
    sections: list[VocabularySection] = Field(default_factory=list)

    @property
    def items(self) -> list[ExtractedVocabularyItem]:
        return [item for section in self.sections for item in section.items]
