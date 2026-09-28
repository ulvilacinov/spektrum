from fastapi import APIRouter

from app.api.dependencies import ChapterServiceDep
from app.schemas.vocabulary import VocabularyItemRead

router = APIRouter(prefix="/chapters", tags=["chapters"])


@router.get("/{chapter_id}/vocabulary", response_model=list[VocabularyItemRead])
def list_chapter_vocabulary(
    chapter_id: int, service: ChapterServiceDep
) -> list[VocabularyItemRead]:
    """The chapter's vocabulary items in the order they appear in the PDF."""
    return [VocabularyItemRead.model_validate(item) for item in service.list_vocabulary(chapter_id)]
