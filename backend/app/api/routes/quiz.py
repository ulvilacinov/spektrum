from fastapi import APIRouter

from app.api.dependencies import AnswerServiceDep, CurrentUserId
from app.schemas.learning import AnswerResultRead, AnswerSubmit

router = APIRouter(prefix="/quiz", tags=["learning"])


@router.post("/{question_id}/answer", response_model=AnswerResultRead)
def answer_question(
    question_id: int,
    payload: AnswerSubmit,
    user_id: CurrentUserId,
    service: AnswerServiceDep,
) -> AnswerResultRead:
    """Evaluate an answer (exact → normalized → AI if needed) and update the word's progress.

    Each question can be answered once. The response reveals the expected answer and a
    Turkish explanation.
    """
    outcome = service.submit(user_id=user_id, question_id=question_id, answer=payload.answer)
    return AnswerResultRead.from_outcome(outcome)
