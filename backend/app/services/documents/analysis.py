import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, UnprocessableError
from app.db.models import Chapter, Document, VocabularyItem
from app.domain.entities import ExtractedPage
from app.domain.enums import DocumentStatus
from app.repositories.chapter_repository import ChapterRepository
from app.repositories.document_repository import DocumentRepository
from app.services.ai.provider import AIProvider
from app.services.ai.schemas import ExtractedVocabularyItem, VocabularyExtractionResult
from app.services.documents.chapter_planning import PlannedChapter, plan_chapters
from app.services.documents.service import DocumentService
from app.services.documents.vocabulary_grounding import ground_items

logger = logging.getLogger(__name__)

MAX_ERROR_MESSAGE_LENGTH = 2000


@dataclass(frozen=True, slots=True)
class _ExtractionJob:
    chapter_index: int
    chapter_title: str
    pages: Sequence[ExtractedPage]
    next_chapter_title: str | None


@dataclass(frozen=True, slots=True)
class AnalysisReport:
    document: Document
    chapters: list[Chapter]
    rejected_item_count: int


class DocumentAnalysisService:
    """Runs the one-time analysis of an uploaded PDF: pages → chapters → vocabulary → DB.

    Status flow: uploaded/failed → parsing → parsed | failed. AI calls run outside any open
    database transaction; results are written in one transaction at the end, so a failed
    analysis never leaves partial chapters behind.
    """

    def __init__(
        self,
        session: Session,
        *,
        documents: DocumentService,
        ai_provider: AIProvider,
        max_pages_per_request: int,
        max_concurrency: int = 1,
    ) -> None:
        self.session = session
        self.documents = documents
        self.document_repository = DocumentRepository(session)
        self.chapter_repository = ChapterRepository(session)
        self.ai = ai_provider
        self.max_pages_per_request = max_pages_per_request
        self.max_concurrency = max_concurrency

    def analyze(self, document_id: int, *, user_id: int, force: bool = False) -> AnalysisReport:
        document = self.documents.get_document(document_id, user_id=user_id)
        self._start_parsing(document, force=force)
        try:
            chapters, rejected_count = self._build_chapters(document_id)
            self.chapter_repository.replace_for_document(document_id, chapters)
            document.status = DocumentStatus.PARSED
            document.processed_at = datetime.now(UTC)
            document.error_message = None
            self.session.commit()
        except AppError as exc:
            self._mark_failed(document, exc.message)
            raise
        except Exception:
            self._mark_failed(document, "Unexpected error during analysis.")
            raise
        self.session.expire(document, ["chapters"])
        return AnalysisReport(
            document=document, chapters=chapters, rejected_item_count=rejected_count
        )

    def _start_parsing(self, document: Document, *, force: bool) -> None:
        allowed = {DocumentStatus.UPLOADED, DocumentStatus.FAILED}
        if force:
            # Also recovers documents stuck in "parsing" after a crashed process.
            allowed |= {DocumentStatus.PARSED, DocumentStatus.PARSING}
        claimed = self.document_repository.transition_status(
            document.id, from_statuses=allowed, to_status=DocumentStatus.PARSING
        )
        self.session.commit()
        self.session.refresh(document)
        if claimed:
            return
        if document.status is DocumentStatus.PARSING:
            message = "The document is already being analyzed."
        else:
            message = "The document has already been analyzed. Use force=true to analyze again."
        raise ConflictError(
            message,
            code="document_not_analyzable",
            details={"document_id": document.id, "status": document.status.value},
        )

    def _build_chapters(self, document_id: int) -> tuple[list[Chapter], int]:
        pages = self.documents.extract_pages(document_id).pages
        text_pages = [page for page in pages if page.has_text]
        if not text_pages:
            raise UnprocessableError(
                "The PDF contains no extractable text. Scanned PDFs need OCR first.",
                code="no_text_layer",
            )

        plan = plan_chapters(self.ai.extract_chapters(text_pages).chapters, len(pages))
        jobs = self._extraction_jobs(plan, pages)
        results = self._run_extraction_jobs(jobs)

        items: list[list[ExtractedVocabularyItem]] = [[] for _ in plan]
        seen: list[set[str]] = [set() for _ in plan]
        rejected_total = 0
        for job, result in zip(jobs, results, strict=True):
            grounding = ground_items(result.items, job.pages)
            rejected_total += len(grounding.rejected)
            for rejected in grounding.rejected:
                logger.warning(
                    "Rejected vocabulary item %r in %r: %s",
                    rejected.item.german,
                    job.chapter_title,
                    rejected.reason,
                )
            for item in grounding.accepted:
                key = " ".join((item.german or "").split()).casefold()
                if key not in seen[job.chapter_index]:
                    seen[job.chapter_index].add(key)
                    items[job.chapter_index].append(item)

        chapters = [_to_chapter(planned, found) for planned, found in zip(plan, items, strict=True)]
        return chapters, rejected_total

    def _extraction_jobs(
        self, plan: Sequence[PlannedChapter], pages: Sequence[ExtractedPage]
    ) -> list[_ExtractionJob]:
        """One AI request per chapter, or per chunk of pages for long chapters."""
        jobs = []
        size = self.max_pages_per_request
        for index, planned in enumerate(plan):
            next_title = plan[index + 1].title if index + 1 < len(plan) else None
            chapter_pages = [
                page for page in pages[planned.start_page - 1 : planned.end_page] if page.has_text
            ]
            for start in range(0, len(chapter_pages), size):
                is_last_chunk = start + size >= len(chapter_pages)
                jobs.append(
                    _ExtractionJob(
                        chapter_index=index,
                        chapter_title=planned.title,
                        pages=chapter_pages[start : start + size],
                        next_chapter_title=next_title if is_last_chunk else None,
                    )
                )
        return jobs

    def _run_extraction_jobs(
        self, jobs: Sequence[_ExtractionJob]
    ) -> list[VocabularyExtractionResult]:
        """Run AI requests concurrently (they are I/O bound); results keep the job order."""
        if not jobs:
            return []
        workers = min(self.max_concurrency, len(jobs))
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="ai-extract") as pool:
            futures = [
                pool.submit(
                    self.ai.extract_vocabulary, job.chapter_title, job.pages, job.next_chapter_title
                )
                for job in jobs
            ]
            try:
                return [future.result() for future in futures]
            except BaseException:
                for future in futures:
                    future.cancel()  # do not start requests whose results would be discarded
                raise

    def _mark_failed(self, document: Document, message: str) -> None:
        try:
            self.session.rollback()
            document.status = DocumentStatus.FAILED
            document.error_message = message[:MAX_ERROR_MESSAGE_LENGTH]
            document.processed_at = datetime.now(UTC)
            self.session.commit()
        except SQLAlchemyError:
            # Keep the original error visible; the document stays "parsing" and can be
            # re-analyzed with force=true.
            logger.exception("Could not mark document %s as failed", document.id)
            self.session.rollback()


def _to_chapter(planned: PlannedChapter, items: Sequence[ExtractedVocabularyItem]) -> Chapter:
    return Chapter(
        title=planned.title,
        chapter_number=planned.chapter_number,
        order=planned.order,
        source_start_page=planned.start_page,
        source_end_page=planned.end_page,
        vocabulary_items=[
            VocabularyItem(**item.model_dump(), order=order)
            for order, item in enumerate(items, start=1)
        ],
    )
