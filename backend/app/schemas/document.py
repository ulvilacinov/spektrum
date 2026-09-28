from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums import DocumentStatus
from app.schemas.chapter import ChapterSummaryRead


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    original_file_name: str
    file_name: str
    status: DocumentStatus
    uploaded_at: datetime
    processed_at: datetime | None
    error_message: str | None


class DocumentAnalysisRead(BaseModel):
    document: DocumentRead
    chapter_count: int
    vocabulary_count: int
    rejected_item_count: int
    chapters: list[ChapterSummaryRead]
