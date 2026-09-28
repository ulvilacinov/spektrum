from pydantic import BaseModel, ConfigDict

from app.domain.enums import VocabularyItemType


class VocabularyItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chapter_id: int
    order: int
    german: str
    turkish: str
    item_type: VocabularyItemType
    article: str | None
    base_verb: str | None
    prateritum: str | None
    perfekt: str | None
    preposition: str | None
    grammatical_case: str | None
    example_german: str | None
    example_turkish: str | None
    source_text: str | None
    source_page: int | None
