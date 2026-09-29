import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id, get_db
from app.core.config import Settings, get_settings
from app.db.models import Chapter, Document, VocabularyItem
from app.domain.enums import DocumentStatus, VocabularyItemType
from app.main import create_app
from app.services.ai import AIProviderError
from tests.fake_ai import FakeAIProvider, chapter, vocab
from tests.pdf_factory import make_pdf

BOOK = [
    "Inhalt\nKapitel 1 ... 2\nKapitel 2 ... 3",
    "Kapitel 1\ndie Veranstaltung\nan einer Konferenz teilnehmen",
    "Kapitel 2\nim Stau stehen",
]


def upload(client: TestClient, pages: list[str] = BOOK) -> int:
    response = client.post(
        "/api/documents", files={"file": ("B1.pdf", make_pdf(pages), "application/pdf")}
    )
    assert response.status_code == 201
    return response.json()["id"]


def analyze(client: TestClient, document_id: int, **params: object):
    return client.post(f"/api/documents/{document_id}/analyze", params=params)


@pytest.fixture
def book_ai(fake_ai: FakeAIProvider) -> FakeAIProvider:
    fake_ai.chapters = [chapter(1, 2), chapter(2, 3)]
    fake_ai.vocabulary = {
        "Kapitel 1": [
            vocab(
                "die Veranstaltung", "etkinlik", 2, item_type=VocabularyItemType.NOUN, article="die"
            ),
            vocab(
                "an einer Konferenz teilnehmen",
                "bir konferansa katılmak",
                2,
                item_type=VocabularyItemType.VERB,
                base_verb="teilnehmen",
                preposition="an",
                grammatical_case="Dativ",
                example_german="Ich nehme morgen an einer Konferenz teil.",
                example_turkish="Yarın bir konferansa katılıyorum.",
            ),
            vocab("der Flughafen", "havalimanı", 2),  # not in the PDF → rejected
            vocab("die Veranstaltung", "etkinlik", 2),  # duplicate → skipped
        ],
        "Kapitel 2": [vocab("im Stau stehen", "trafikte kalmak", 3)],
    }
    return fake_ai


def test_analyze_stores_chapters_and_grounded_vocabulary(
    client: TestClient, sqlite_session: Session, book_ai: FakeAIProvider
) -> None:
    document_id = upload(client)

    response = analyze(client, document_id)

    assert response.status_code == 200
    body = response.json()
    assert body["document"]["status"] == "parsed"
    assert body["document"]["processed_at"] is not None
    assert body["chapter_count"] == 2
    assert body["vocabulary_count"] == 3
    assert body["rejected_item_count"] == 1
    assert [
        (
            c["chapter_number"],
            c["title"],
            c["source_start_page"],
            c["source_end_page"],
            c["vocabulary_count"],
        )
        for c in body["chapters"]
    ] == [(1, "Kapitel 1", 2, 2, 2), (2, "Kapitel 2", 3, 3, 1)]

    items = sqlite_session.scalars(
        select(VocabularyItem).join(Chapter).order_by(Chapter.order, VocabularyItem.order)
    ).all()
    assert [(i.german, i.order, i.source_page) for i in items] == [
        ("die Veranstaltung", 1, 2),
        ("an einer Konferenz teilnehmen", 2, 2),
        ("im Stau stehen", 1, 3),
    ]
    verb = items[1]
    assert verb.item_type is VocabularyItemType.VERB
    assert (verb.base_verb, verb.preposition, verb.grammatical_case) == (
        "teilnehmen",
        "an",
        "Dativ",
    )
    assert verb.example_turkish == "Yarın bir konferansa katılıyorum."
    assert verb.source_text == "an einer Konferenz teilnehmen"


def test_ai_receives_text_pages_and_chapter_boundaries(
    client: TestClient, book_ai: FakeAIProvider
) -> None:
    analyze(client, upload(client, [*BOOK, ""]))

    assert book_ai.chapter_calls == [[1, 2, 3]]  # the blank page 4 is not sent
    assert sorted(book_ai.vocabulary_calls) == [
        ("Kapitel 1", [2], "Kapitel 2"),
        ("Kapitel 2", [3], None),
    ]


def test_long_chapters_are_sent_in_chunks(
    client: TestClient, settings: Settings, fake_ai: FakeAIProvider
) -> None:
    settings.ai_max_pages_per_request = 2
    fake_ai.chapters = [chapter(1, 1)]
    fake_ai.vocabulary = {"Kapitel 1": [vocab(f"Wort{n}", f"kelime{n}", n) for n in range(1, 6)]}

    body = analyze(
        client, upload(client, ["Kapitel 1\nWort1", *[f"Wort{n}" for n in range(2, 6)]])
    ).json()

    assert sorted(fake_ai.vocabulary_calls) == [
        ("Kapitel 1", [1, 2], None),
        ("Kapitel 1", [3, 4], None),
        ("Kapitel 1", [5], None),
    ]
    assert body["vocabulary_count"] == 5


def test_document_without_chapters_becomes_one_chapter(
    client: TestClient, fake_ai: FakeAIProvider
) -> None:
    fake_ai.vocabulary = {"Wortschatz": [vocab("die Veranstaltung", "etkinlik", 1)]}

    body = analyze(client, upload(client, ["die Veranstaltung", "mehr"])).json()

    assert [(c["title"], c["chapter_number"], c["source_end_page"]) for c in body["chapters"]] == [
        ("Wortschatz", None, 2)
    ]


def test_already_parsed_document_needs_force(client: TestClient, book_ai: FakeAIProvider) -> None:
    document_id = upload(client)
    analyze(client, document_id)

    response = analyze(client, document_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "document_not_analyzable"
    assert response.json()["error"]["details"]["status"] == "parsed"


def test_force_replaces_previous_results(
    client: TestClient, sqlite_session: Session, book_ai: FakeAIProvider
) -> None:
    document_id = upload(client)
    analyze(client, document_id)
    book_ai.chapters = [chapter(1, 2)]

    response = analyze(client, document_id, force=True)

    assert response.status_code == 200
    assert response.json()["chapter_count"] == 1
    assert [c.title for c in sqlite_session.scalars(select(Chapter))] == ["Kapitel 1"]
    # Kapitel 1 now spans pages 2-3, but "im Stau stehen" is not a Kapitel 1 item.
    assert [i.german for i in sqlite_session.scalars(select(VocabularyItem))] == [
        "die Veranstaltung",
        "an einer Konferenz teilnehmen",
    ]


def test_document_in_progress_is_rejected(
    client: TestClient, sqlite_session: Session, book_ai: FakeAIProvider
) -> None:
    document_id = upload(client)
    sqlite_session.get(Document, document_id).status = DocumentStatus.PARSING
    sqlite_session.commit()

    response = analyze(client, document_id)

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "The document is already being analyzed."


def test_ai_failure_marks_document_failed_and_can_be_retried(
    client: TestClient, sqlite_session: Session, book_ai: FakeAIProvider
) -> None:
    document_id = upload(client)
    book_ai.error = AIProviderError("The AI service request failed.")

    response = analyze(client, document_id)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ai_provider_error"
    document = client.get(f"/api/documents/{document_id}").json()
    assert document["status"] == "failed"
    assert document["error_message"] == "The AI service request failed."
    assert sqlite_session.scalars(select(Chapter)).all() == []

    book_ai.error = None
    retried = analyze(client, document_id)
    assert retried.status_code == 200
    assert retried.json()["document"]["error_message"] is None


def test_pdf_without_text_fails(client: TestClient, fake_ai: FakeAIProvider) -> None:
    document_id = upload(client, ["", ""])

    response = analyze(client, document_id)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "no_text_layer"
    assert client.get(f"/api/documents/{document_id}").json()["status"] == "failed"
    assert fake_ai.chapter_calls == []


def test_analyze_unknown_document(client: TestClient) -> None:
    assert analyze(client, 999).status_code == 404


def test_analyze_without_api_key_is_unavailable(
    sqlite_session: Session, settings: Settings
) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: sqlite_session
    app.dependency_overrides[get_settings] = lambda: settings  # gemini_api_key=None
    app.dependency_overrides[get_current_user_id] = lambda: 1
    with TestClient(app) as client:
        document_id = upload(client)
        response = analyze(client, document_id)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_not_configured"
    assert sqlite_session.get(Document, document_id).status is DocumentStatus.UPLOADED


def test_items_keep_page_order_across_concurrent_chunks(
    client: TestClient, sqlite_session: Session, settings: Settings, fake_ai: FakeAIProvider
) -> None:
    settings.ai_max_pages_per_request = 1
    fake_ai.chapters = [chapter(1, 1)]
    fake_ai.vocabulary = {"Kapitel 1": [vocab(f"Wort{n}", f"kelime{n}", n) for n in range(1, 7)]}
    document_id = upload(client, ["Kapitel 1\nWort1", *[f"Wort{n}" for n in range(2, 7)]])

    analyze(client, document_id)

    items = sqlite_session.scalars(select(VocabularyItem).order_by(VocabularyItem.order)).all()
    assert [(i.order, i.german, i.source_page) for i in items] == [
        (n, f"Wort{n}", n) for n in range(1, 7)
    ]


def test_one_failed_chunk_fails_the_whole_analysis(
    client: TestClient, sqlite_session: Session, settings: Settings, fake_ai: FakeAIProvider
) -> None:
    settings.ai_max_pages_per_request = 1
    fake_ai.chapters = [chapter(1, 1)]
    original = fake_ai.extract_vocabulary

    def flaky(chapter_title, pages, next_chapter_title=None):
        if pages[0].page_number == 2:
            raise AIProviderError("The AI service request failed.")
        return original(chapter_title, pages, next_chapter_title)

    fake_ai.extract_vocabulary = flaky
    document_id = upload(client, ["Kapitel 1", "Wort", "Wort"])

    assert analyze(client, document_id).status_code == 502
    assert client.get(f"/api/documents/{document_id}").json()["status"] == "failed"
    assert sqlite_session.scalars(select(Chapter)).all() == []
