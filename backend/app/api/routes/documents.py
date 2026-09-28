from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile, status

from app.api.dependencies import (
    ChapterServiceDep,
    DocumentAnalysisServiceDep,
    DocumentServiceDep,
)
from app.schemas.chapter import ChapterSummaryRead
from app.schemas.document import DocumentAnalysisRead, DocumentRead
from app.services.documents import AnalysisReport

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def upload_document(
    service: DocumentServiceDep,
    file: Annotated[UploadFile, File(description="Vocabulary PDF")],
) -> DocumentRead:
    document = service.upload(
        file=file.file, filename=file.filename, content_type=file.content_type
    )
    return DocumentRead.model_validate(document)


@router.get("", response_model=list[DocumentRead])
def list_documents(
    service: DocumentServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DocumentRead]:
    documents = service.list_documents(limit=limit, offset=offset)
    return [DocumentRead.model_validate(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: int, service: DocumentServiceDep) -> DocumentRead:
    return DocumentRead.model_validate(service.get_document(document_id))


@router.get("/{document_id}/chapters", response_model=list[ChapterSummaryRead])
def list_document_chapters(
    document_id: int, service: ChapterServiceDep
) -> list[ChapterSummaryRead]:
    """Chapters in reading order with their vocabulary counts (empty before analysis)."""
    return [
        ChapterSummaryRead.from_chapter(chapter, count)
        for chapter, count in service.list_for_document(document_id)
    ]


@router.post("/{document_id}/analyze", response_model=DocumentAnalysisRead)
def analyze_document(
    document_id: int,
    service: DocumentAnalysisServiceDep,
    force: Annotated[
        bool, Query(description="Analyze again even if the document was already analyzed.")
    ] = False,
) -> DocumentAnalysisRead:
    """Detect chapters and extract vocabulary with the AI provider (runs synchronously)."""
    return _analysis_response(service.analyze(document_id, force=force))


def _analysis_response(report: AnalysisReport) -> DocumentAnalysisRead:
    chapters = [
        ChapterSummaryRead.from_chapter(chapter, len(chapter.vocabulary_items))
        for chapter in report.chapters
    ]
    return DocumentAnalysisRead(
        document=DocumentRead.model_validate(report.document),
        chapter_count=len(chapters),
        vocabulary_count=sum(chapter.vocabulary_count for chapter in chapters),
        rejected_item_count=report.rejected_item_count,
        chapters=chapters,
    )
