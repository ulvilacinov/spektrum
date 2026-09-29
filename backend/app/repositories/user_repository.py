from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import AuthSession, User


class UserRepository:
    """Users and their login sessions. Never commits; the calling service owns the transaction."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        return self.session.scalar(select(User).where(User.username == username))

    def list(self) -> Sequence[User]:
        return self.session.scalars(select(User).order_by(User.id)).all()

    def add(self, *objects: User | AuthSession) -> None:
        self.session.add_all(objects)
        self.session.flush()

    def session_by_token_hash(self, token_hash: str) -> AuthSession | None:
        return self.session.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))

    def delete_session(self, token_hash: str) -> None:
        self.session.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash))

    def delete_sessions_of(self, user_id: int) -> None:
        self.session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))

    def delete_expired_sessions(self, now: datetime) -> None:
        self.session.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
