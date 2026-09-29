import re
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NotAuthenticatedError,
    NotFoundError,
    TooManyRequestsError,
    UnprocessableError,
)
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    new_session_token,
    token_hash,
    verify_password,
)
from app.db.models import AuthSession, User
from app.repositories.user_repository import UserRepository

USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 256
# A session is extended on use once less than this much of its lifetime has passed.
REFRESH_AFTER = timedelta(days=1)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes; PostgreSQL returns aware ones.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


class LoginThrottle:
    """Slows down password guessing: too many recent failures block further attempts.

    Counted per username and per client address. In memory, so it resets on restart; the
    app runs as a single process.
    """

    def __init__(
        self,
        *,
        max_per_username: int = 5,
        max_per_client: int = 20,
        window_seconds: float = 15 * 60,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limits = {"user": max_per_username, "client": max_per_client}
        self.window = window_seconds
        self.clock = clock
        self._failures: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _keys(self, username: str, client: str) -> list[tuple[str, str]]:
        return [("user", username), ("client", client)]

    def check(self, username: str, client: str) -> None:
        now = self.clock()
        with self._lock:
            for key in self._keys(username, client):
                failures = self._failures[key]
                while failures and failures[0] <= now - self.window:
                    failures.popleft()
                if len(failures) >= self.limits[key[0]]:
                    retry_after = int(failures[0] + self.window - now) + 1
                    raise TooManyRequestsError(
                        "Too many failed login attempts. Try again later.",
                        code="too_many_login_attempts",
                        details={"retry_after_seconds": retry_after},
                    )

    def failed(self, username: str, client: str) -> None:
        now = self.clock()
        with self._lock:
            for key in self._keys(username, client):
                self._failures[key].append(now)

    def succeeded(self, username: str) -> None:
        with self._lock:
            self._failures.pop(("user", username), None)


@dataclass(frozen=True, slots=True)
class LoginResult:
    user: User
    token: str
    expires_at: datetime


class AuthService:
    """Accounts, logins and cookie sessions."""

    def __init__(
        self,
        session: Session,
        *,
        session_lifetime: timedelta,
        throttle: LoginThrottle,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.session_lifetime = session_lifetime
        self.throttle = throttle
        self.clock = clock

    # -- logins -------------------------------------------------------------------------

    def login(self, *, username: str, password: str, client: str) -> LoginResult:
        name = username.strip().lower()
        self.throttle.check(name, client)
        user = self.users.get_by_username(name)
        # Hash even for unknown users so the response time does not reveal which names exist.
        valid = verify_password(password, user.password_hash if user else DUMMY_PASSWORD_HASH)
        if user is None or not valid:
            self.throttle.failed(name, client)
            raise NotAuthenticatedError("Wrong username or password.", code="invalid_credentials")
        self.throttle.succeeded(name)

        now = self.clock()
        token = new_session_token()
        expires_at = now + self.session_lifetime
        self.users.delete_expired_sessions(now)
        self.users.add(
            AuthSession(user_id=user.id, token_hash=token_hash(token), expires_at=expires_at)
        )
        self.session.commit()
        return LoginResult(user=user, token=token, expires_at=expires_at)

    def authenticate(self, token: str | None) -> User:
        """The user of a session cookie; extends sessions that are in use."""
        if not token:
            raise NotAuthenticatedError("Login required.")
        auth_session = self.users.session_by_token_hash(token_hash(token))
        now = self.clock()
        if auth_session is None or _as_utc(auth_session.expires_at) <= now:
            raise NotAuthenticatedError("The session has expired. Please log in again.")
        renewed = now + self.session_lifetime
        if renewed - _as_utc(auth_session.expires_at) >= REFRESH_AFTER:
            auth_session.expires_at = renewed
            self.session.commit()
        user = self.users.get(auth_session.user_id)
        if user is None:
            raise NotAuthenticatedError("Login required.")
        return user

    def logout(self, token: str | None) -> None:
        if token:
            self.users.delete_session(token_hash(token))
            self.session.commit()

    # -- accounts (CLI) -----------------------------------------------------------------

    def create_user(self, *, username: str, password: str) -> User:
        name = self._valid_username(username)
        if self.users.get_by_username(name) is not None:
            raise ConflictError(f"User {name!r} already exists.", code="user_exists")
        user = User(username=name, password_hash=hash_password(self._valid_password(password)))
        self.users.add(user)
        self.session.commit()
        return user

    def set_password(self, *, username: str, password: str) -> User:
        """Change a password and end all of the user's sessions."""
        user = self._require_user(username)
        user.password_hash = hash_password(self._valid_password(password))
        self.users.delete_sessions_of(user.id)
        self.session.commit()
        return user

    def rename_user(self, *, username: str, new_username: str) -> User:
        user = self._require_user(username)
        name = self._valid_username(new_username)
        if name != user.username and self.users.get_by_username(name) is not None:
            raise ConflictError(f"User {name!r} already exists.", code="user_exists")
        user.username = name
        self.session.commit()
        return user

    def list_users(self) -> list[User]:
        return list(self.users.list())

    def _require_user(self, username: str) -> User:
        user = self.users.get_by_username(username.strip().lower())
        if user is None:
            raise NotFoundError(f"User {username!r} was not found.")
        return user

    @staticmethod
    def _valid_username(username: str) -> str:
        name = username.strip().lower()
        if not USERNAME_PATTERN.match(name):
            raise UnprocessableError(
                "Usernames have 3-32 characters: letters, digits, '.', '_' or '-'.",
                code="invalid_username",
            )
        return name

    @staticmethod
    def _valid_password(password: str) -> str:
        if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
            raise UnprocessableError(
                f"Passwords need at least {MIN_PASSWORD_LENGTH} characters.",
                code="invalid_password",
            )
        return password
