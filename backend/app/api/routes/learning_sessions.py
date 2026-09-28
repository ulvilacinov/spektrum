from fastapi import APIRouter, Response, status

from app.api.dependencies import CurrentUserId, LearningSessionServiceDep, QuizServiceDep
from app.schemas.learning import (
    LearningSessionCreate,
    LearningSessionItemRead,
    LearningSessionRead,
    QuizRead,
)

router = APIRouter(prefix="/learning-sessions", tags=["learning"])


@router.post("", response_model=LearningSessionRead, status_code=status.HTTP_201_CREATED)
def start_learning_session(
    payload: LearningSessionCreate,
    user_id: CurrentUserId,
    service: LearningSessionServiceDep,
) -> LearningSessionRead:
    """Start a batch with the chapter's next 5/10/20 unstudied words (they become learning)."""
    learning_session = service.start(
        user_id=user_id, chapter_id=payload.chapter_id, batch_size=payload.batch_size
    )
    return LearningSessionRead.from_session(learning_session)


@router.get("/{learning_session_id}/items", response_model=list[LearningSessionItemRead])
def list_learning_session_items(
    learning_session_id: int,
    user_id: CurrentUserId,
    service: LearningSessionServiceDep,
) -> list[LearningSessionItemRead]:
    """The words of the batch in display order, with their current learning status."""
    items = service.items(user_id=user_id, learning_session_id=learning_session_id)
    return [LearningSessionItemRead.from_item(item) for item in items]


@router.post(
    "/{learning_session_id}/quiz",
    response_model=QuizRead,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": QuizRead, "description": "The quiz already existed."}},
)
def create_quiz(
    learning_session_id: int,
    user_id: CurrentUserId,
    service: QuizServiceDep,
    response: Response,
) -> QuizRead:
    """Create the batch's quiz (one question per word); calling it again returns the same quiz."""
    quiz = service.get_or_create(user_id=user_id, learning_session_id=learning_session_id)
    if not quiz.created:
        response.status_code = status.HTTP_200_OK
    return QuizRead.from_quiz(quiz)
