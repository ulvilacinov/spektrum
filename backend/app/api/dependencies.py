from collections.abc import Callable, Iterator
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.crypto import SecretBox
from app.db.models import User
from app.db.session import SessionLocal
from app.services.ai import AIProvider, create_ai_provider
from app.services.ai_settings import AISettingsService, ProviderBuilder
from app.services.auth import AuthService, LoginThrottle
from app.services.chat import ChatService
from app.services.documents import (
    ChapterService,
    DocumentAnalysisService,
    DocumentService,
    LocalFileStorage,
)
from app.services.learning import (
    AnswerService,
    LearningSessionService,
    ProgressionPolicy,
    ProgressService,
    QuizService,
    SimpleProgressionPolicy,
)
from app.services.pdf import PdfTextExtractor


def get_db() -> Iterator[Session]:
    """One session per request. Services decide when to commit."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


# One throttle for the whole process (failed logins must be counted across requests).
_login_throttle = LoginThrottle()


def get_auth_service(db: DbSession, settings: AppSettings) -> AuthService:
    return AuthService(
        db, session_lifetime=timedelta(days=settings.session_days), throttle=_login_throttle
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def session_token(request: Request, settings: Settings) -> str | None:
    return request.cookies.get(settings.session_cookie_name)


def get_current_user(request: Request, settings: AppSettings, auth: AuthServiceDep) -> User:
    """The logged-in user (401 ``not_authenticated`` without a valid session cookie)."""
    return auth.authenticate(session_token(request, settings))


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_user_id(user: CurrentUser) -> int:
    """The acting user's id; every data access is scoped to it."""
    return user.id


CurrentUserId = Annotated[int, Depends(get_current_user_id)]


def get_document_service(db: DbSession, settings: AppSettings) -> DocumentService:
    return DocumentService(
        db,
        storage=LocalFileStorage(settings.upload_dir),
        extractor=PdfTextExtractor(),
        max_upload_bytes=settings.max_upload_size_mb * 1024 * 1024,
    )


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


def get_chapter_service(db: DbSession) -> ChapterService:
    return ChapterService(db)


ChapterServiceDep = Annotated[ChapterService, Depends(get_chapter_service)]


def get_provider_builder(settings: AppSettings) -> ProviderBuilder:
    """How an AI configuration becomes a provider (tests replace it with a fake)."""
    return lambda config: create_ai_provider(config, settings)


def get_ai_settings_service(
    db: DbSession,
    settings: AppSettings,
    build_provider: Annotated[ProviderBuilder, Depends(get_provider_builder)],
) -> AISettingsService:
    return AISettingsService(
        db, secret_box=SecretBox.from_settings(settings), build_provider=build_provider
    )


AISettingsServiceDep = Annotated[AISettingsService, Depends(get_ai_settings_service)]


def get_ai_provider_factory(
    user_id: CurrentUserId,
    ai_settings: AISettingsServiceDep,
) -> Callable[[], AIProvider]:
    """The user's AI, built on first use: deterministic paths work without an AI setup."""
    return lambda: ai_settings.provider_for(user_id)


def get_ai_provider(
    factory: Annotated[Callable[[], AIProvider], Depends(get_ai_provider_factory)],
) -> AIProvider:
    return factory()


AIProviderDep = Annotated[AIProvider, Depends(get_ai_provider)]


def get_document_analysis_service(
    db: DbSession,
    settings: AppSettings,
    documents: DocumentServiceDep,
    ai_provider: AIProviderDep,
) -> DocumentAnalysisService:
    return DocumentAnalysisService(
        db,
        documents=documents,
        ai_provider=ai_provider,
        max_pages_per_request=settings.ai_max_pages_per_request,
        max_concurrency=settings.ai_max_concurrency,
    )


DocumentAnalysisServiceDep = Annotated[
    DocumentAnalysisService, Depends(get_document_analysis_service)
]


def get_progression_policy() -> ProgressionPolicy:
    """The learning-progression rules; swap here for e.g. spaced repetition."""
    return SimpleProgressionPolicy()


def get_learning_session_service(
    db: DbSession,
    policy: Annotated[ProgressionPolicy, Depends(get_progression_policy)],
) -> LearningSessionService:
    return LearningSessionService(db, policy=policy)


LearningSessionServiceDep = Annotated[LearningSessionService, Depends(get_learning_session_service)]


def get_quiz_service(db: DbSession, sessions: LearningSessionServiceDep) -> QuizService:
    return QuizService(db, sessions=sessions)


QuizServiceDep = Annotated[QuizService, Depends(get_quiz_service)]


def get_answer_service(
    db: DbSession,
    policy: Annotated[ProgressionPolicy, Depends(get_progression_policy)],
    ai_provider_factory: Annotated[Callable[[], AIProvider], Depends(get_ai_provider_factory)],
) -> AnswerService:
    return AnswerService(db, policy=policy, ai_provider_factory=ai_provider_factory)


AnswerServiceDep = Annotated[AnswerService, Depends(get_answer_service)]


def get_progress_service(
    db: DbSession, policy: Annotated[ProgressionPolicy, Depends(get_progression_policy)]
) -> ProgressService:
    return ProgressService(db, policy=policy)


ProgressServiceDep = Annotated[ProgressService, Depends(get_progress_service)]


def get_chat_service(
    ai_provider_factory: Annotated[Callable[[], AIProvider], Depends(get_ai_provider_factory)],
) -> ChatService:
    return ChatService(ai_provider_factory=ai_provider_factory)


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
