from fastapi import APIRouter

from app.api.dependencies import ChapterServiceDep, CurrentUserId
from app.schemas.vocabulary import VocabularyItemRead

router = APIRouter(prefix="/chapters", tags=["chapters"])


@router.get("/{chapter_id}/vocabulary", response_model=list[VocabularyItemRead])
def list_chapter_vocabulary(
    chapter_id: int, service: ChapterServiceDep, user_id: CurrentUserId
) -> list[VocabularyItemRead]:
    """The chapter's vocabulary items in the order they appear in the PDF."""
    items = service.list_vocabulary(chapter_id, user_id=user_id)
    return [VocabularyItemRead.model_validate(item) for item in items]
