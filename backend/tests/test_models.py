from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chapter, Document, VocabularyItem
from app.domain.enums import DocumentStatus, VocabularyItemType


def test_document_chapter_vocabulary_roundtrip(sqlite_session: Session) -> None:
    document = Document(
        file_name="abc123.pdf",
        original_file_name="Wortschatz B1.pdf",
        storage_path="uploads/abc123.pdf",
    )
    chapter = Chapter(
        title="Kapitel 1", chapter_number=1, order=1, source_start_page=1, source_end_page=4
    )
    chapter.vocabulary_items.append(
        VocabularyItem(
            german="an einer Konferenz teilnehmen",
            turkish="bir konferansa katılmak",
            item_type=VocabularyItemType.VERB,
            base_verb="teilnehmen",
            preposition="an",
            grammatical_case="Dativ",
            source_page=1,
            order=1,
        )
    )
    document.chapters.append(chapter)
    sqlite_session.add(document)
    sqlite_session.commit()

    stored = sqlite_session.scalars(select(Document)).one()
    assert stored.status is DocumentStatus.UPLOADED
    assert stored.uploaded_at is not None
    assert [c.title for c in stored.chapters] == ["Kapitel 1"]

    item = stored.chapters[0].vocabulary_items[0]
    assert item.item_type is VocabularyItemType.VERB
    assert item.chapter.document.id == stored.id
