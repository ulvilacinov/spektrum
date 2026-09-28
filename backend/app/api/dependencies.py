from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.services.ai import AIProvider, create_ai_provider
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


def get_ai_provider(settings: AppSettings) -> AIProvider:
    return create_ai_provider(settings)


AIProviderDep = Annotated[AIProvider, Depends(get_ai_provider)]


def get_ai_provider_factory(settings: AppSettings) -> Callable[[], AIProvider]:
    """For services that need the AI only sometimes: build the provider on first use."""
    return lambda: create_ai_provider(settings)


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


def get_current_user_id(settings: AppSettings) -> int:
    """The acting user. The single seam to replace once authentication exists."""
    return settings.default_user_id


CurrentUserId = Annotated[int, Depends(get_current_user_id)]


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
