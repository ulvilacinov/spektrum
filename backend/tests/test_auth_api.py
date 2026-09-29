from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_ai_provider,
    get_ai_provider_factory,
    get_auth_service,
    get_db,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, UnprocessableError
from app.db.models import AuthSession
from app.main import create_app
from app.services.auth import AuthService, LoginThrottle
from tests.fake_ai import FakeAIProvider
from tests.pdf_factory import make_pdf

PASSWORD = "richtig-geheim"


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def throttle() -> LoginThrottle:
    return LoginThrottle()


@pytest.fixture
def auth(sqlite_session: Session, clock: Clock, throttle: LoginThrottle) -> AuthService:
    return AuthService(
        sqlite_session, session_lifetime=timedelta(days=30), throttle=throttle, clock=clock
    )


@pytest.fixture
def app_client(
    sqlite_session: Session, settings: Settings, auth: AuthService, fake_ai: FakeAIProvider
) -> Iterator[TestClient]:
    """A client without a login override: requests go through the real cookie session."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: sqlite_session
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_auth_service] = lambda: auth
    app.dependency_overrides[get_ai_provider] = lambda: fake_ai
    app.dependency_overrides[get_ai_provider_factory] = lambda: lambda: fake_ai
    with TestClient(app) as client:
        yield client


@pytest.fixture
def anna(auth: AuthService) -> str:
    auth.create_user(username="Anna", password=PASSWORD)
    return "anna"


def login(client: TestClient, username: str = "anna", password: str = PASSWORD):
    return client.post("/api/auth/login", json={"username": username, "password": password})


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/documents"),
        ("get", "/api/progress"),
        ("get", "/api/review/weak"),
        ("get", "/api/chapters/1/vocabulary"),
        ("post", "/api/chat"),
        ("get", "/api/auth/me"),
    ],
)
def test_everything_but_health_needs_a_login(
    app_client: TestClient, method: str, path: str
) -> None:
    response = getattr(app_client, method)(path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_health_is_open(app_client: TestClient) -> None:
    assert app_client.get("/api/health").status_code in (200, 503)


def test_login_sets_an_http_only_session_cookie(
    app_client: TestClient, anna: str, settings: Settings
) -> None:
    response = login(app_client, username="  ANNA ")

    assert response.status_code == 200
    assert response.json()["username"] == "anna"
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{settings.session_cookie_name}=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" not in cookie  # local HTTP; production enables it
    assert app_client.get("/api/auth/me").json()["username"] == "anna"
    assert app_client.get("/api/documents").status_code == 200


def test_secure_cookie_when_configured(
    app_client: TestClient, anna: str, settings: Settings
) -> None:
    settings.session_cookie_secure = True

    assert "Secure" in login(app_client).headers["set-cookie"]


@pytest.mark.parametrize(
    ("username", "password"), [("anna", "falsch-falsch"), ("nobody", PASSWORD)]
)
def test_wrong_credentials_look_the_same(
    app_client: TestClient, anna: str, username: str, password: str
) -> None:
    response = login(app_client, username, password)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"
    assert "set-cookie" not in response.headers


def test_accounts_without_a_password_cannot_log_in(app_client: TestClient) -> None:
    # The conftest user (like the migration's "admin") has an empty password hash.
    assert login(app_client, "learner", "").status_code == 422
    assert login(app_client, "learner", "anything").status_code == 401


def test_logout_ends_the_session(app_client: TestClient, anna: str, settings: Settings) -> None:
    login(app_client)
    token = app_client.cookies[settings.session_cookie_name]

    response = app_client.post("/api/auth/logout")

    assert response.status_code == 204
    assert app_client.get("/api/auth/me").status_code == 401
    app_client.cookies.set(settings.session_cookie_name, token)  # replaying the old cookie
    assert app_client.get("/api/auth/me").status_code == 401


def test_repeated_failures_are_throttled(app_client: TestClient, anna: str) -> None:
    for _ in range(5):
        assert login(app_client, password="falsch-falsch").status_code == 401

    response = login(app_client)  # even the right password is refused for a while

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "too_many_login_attempts"
    assert response.json()["error"]["details"]["retry_after_seconds"] > 0


def test_throttle_forgets_old_failures() -> None:
    now = [0.0]
    throttle = LoginThrottle(max_per_username=2, window_seconds=60, clock=lambda: now[0])
    throttle.failed("anna", "1.2.3.4")
    throttle.failed("anna", "1.2.3.4")
    with pytest.raises(Exception, match="Too many"):
        throttle.check("anna", "1.2.3.4")

    now[0] = 61
    throttle.check("anna", "1.2.3.4")


def test_sessions_expire_and_are_extended_while_used(
    app_client: TestClient, anna: str, clock: Clock, sqlite_session: Session
) -> None:
    login(app_client)
    clock.now += timedelta(days=20)
    assert app_client.get("/api/auth/me").status_code == 200  # used: extended to day 50

    clock.now += timedelta(days=25)
    assert app_client.get("/api/auth/me").status_code == 200

    clock.now += timedelta(days=31)
    assert app_client.get("/api/auth/me").status_code == 401
    assert sqlite_session.query(AuthSession).count() == 1  # removed at the next login


def test_changing_the_password_logs_out_everywhere(
    app_client: TestClient, anna: str, auth: AuthService
) -> None:
    login(app_client)

    auth.set_password(username="anna", password="neues-passwort")

    assert app_client.get("/api/auth/me").status_code == 401
    assert login(app_client, password="neues-passwort").status_code == 200


def test_users_only_see_their_own_documents(
    app_client: TestClient, anna: str, auth: AuthService
) -> None:
    auth.create_user(username="bob", password=PASSWORD)
    login(app_client)
    uploaded = app_client.post(
        "/api/documents", files={"file": ("B1.pdf", make_pdf(["Kapitel 1"]), "application/pdf")}
    ).json()
    app_client.post("/api/auth/logout")

    login(app_client, "bob")

    assert app_client.get("/api/documents").json() == []
    document = f"/api/documents/{uploaded['id']}"
    assert app_client.get(document).status_code == 404
    assert app_client.get(f"{document}/chapters").status_code == 404
    assert app_client.post(f"{document}/analyze").status_code == 404
    assert (
        app_client.get("/api/progress", params={"document_id": uploaded["id"]}).status_code == 404
    )


def test_account_rules(auth: AuthService) -> None:
    with pytest.raises(UnprocessableError):
        auth.create_user(username="a", password=PASSWORD)
    with pytest.raises(UnprocessableError):
        auth.create_user(username="anna", password="kurz")
    auth.create_user(username="anna", password=PASSWORD)
    with pytest.raises(ConflictError):
        auth.create_user(username="ANNA", password=PASSWORD)
    renamed = auth.rename_user(username="anna", new_username="anna.k")
    assert renamed.username == "anna.k"
