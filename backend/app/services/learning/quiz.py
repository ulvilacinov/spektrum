from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import LearningSession, QuizQuestion
from app.repositories.learning_repository import LearningRepository
from app.services.learning.question_generation import generate_questions
from app.services.learning.sessions import LearningSessionService


@dataclass(frozen=True, slots=True)
class Quiz:
    learning_session: LearningSession
    questions: list[QuizQuestion]
    created: bool


class QuizService:
    """Creates the quiz of a learning session once; later calls return the same quiz."""

    def __init__(self, session: Session, *, sessions: LearningSessionService) -> None:
        self.session = session
        self.sessions = sessions
        self.learning = LearningRepository(session)

    def get_or_create(self, *, user_id: int, learning_session_id: int) -> Quiz:
        learning_session = self.sessions.get(
            user_id=user_id, learning_session_id=learning_session_id
        )
        existing = self.learning.quiz_questions(learning_session.id)
        if existing:
            return Quiz(learning_session, list(existing), created=False)

        vocabulary = [item for _, item in self.learning.session_items(learning_session.id)]
        questions = [
            QuizQuestion(
                learning_session_id=learning_session.id,
                position=position,
                vocabulary_item_id=draft.vocabulary_item_id,
                question_type=draft.question_type,
                question=draft.question,
                expected_answer=draft.expected_answer,
            )
            for position, draft in enumerate(
                generate_questions(vocabulary, seed=learning_session.id), start=1
            )
        ]
        try:
            self.learning.add(*questions)
            self.session.commit()
        except IntegrityError:
            # A concurrent request created the quiz first; return that one.
            self.session.rollback()
            return Quiz(
                learning_session,
                list(self.learning.quiz_questions(learning_session.id)),
                created=False,
            )
        return Quiz(learning_session, questions, created=True)
