from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentUserId, ProgressServiceDep
from app.schemas.progress import ProgressRead, WeakWordRead

router = APIRouter(tags=["progress"])


@router.get("/progress", response_model=ProgressRead)
def get_progress(
    user_id: CurrentUserId,
    service: ProgressServiceDep,
    document_id: Annotated[int | None, Query(description="Only this document's chapters.")] = None,
) -> ProgressRead:
    """Word counts per status for every chapter, and whether a new batch or review can start."""
    chapters = service.chapter_progress(user_id=user_id, document_id=document_id)
    return ProgressRead.from_chapters(chapters)


@router.get("/review/weak", response_model=list[WeakWordRead])
def list_weak_words(
    user_id: CurrentUserId,
    service: ProgressServiceDep,
    document_id: int | None = None,
    chapter_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[WeakWordRead]:
    """Weak words (longest due first) with the latest mistake and its Turkish explanation.

    Review them with POST /api/learning-sessions using mode=review.
    """
    words = service.weak_words(
        user_id=user_id, document_id=document_id, chapter_id=chapter_id, limit=limit
    )
    return [WeakWordRead.from_weak_word(word) for word in words]
