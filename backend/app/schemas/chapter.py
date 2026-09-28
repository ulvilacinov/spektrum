from typing import Self

from pydantic import BaseModel

from app.db.models import Chapter


class ChapterSummaryRead(BaseModel):
    id: int
    chapter_number: int | None
    title: str
    order: int
    source_start_page: int
    source_end_page: int
    vocabulary_count: int

    @classmethod
    def from_chapter(cls, chapter: Chapter, vocabulary_count: int) -> Self:
        return cls(
            id=chapter.id,
            chapter_number=chapter.chapter_number,
            title=chapter.title,
            order=chapter.order,
            source_start_page=chapter.source_start_page,
            source_end_page=chapter.source_end_page,
            vocabulary_count=vocabulary_count,
        )
