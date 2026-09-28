from fastapi.testclient import TestClient

from app.domain.enums import VocabularyItemType
from tests.fake_ai import FakeAIProvider, chapter, vocab
from tests.pdf_factory import make_pdf

BOOK = [
    "Kapitel 1\ndie Veranstaltung\nan einer Konferenz teilnehmen",
    "Kapitel 2\nim Stau stehen",
    "Kapitel 3\nnur Übungen",
]


def analyzed_document(client: TestClient, fake_ai: FakeAIProvider) -> int:
    fake_ai.chapters = [chapter(1, 1), chapter(2, 2), chapter(3, 3)]
    fake_ai.vocabulary = {
        "Kapitel 1": [
            vocab(
                "die Veranstaltung", "etkinlik", 1, item_type=VocabularyItemType.NOUN, article="die"
            ),
            vocab(
                "an einer Konferenz teilnehmen",
                "bir konferansa katılmak",
                1,
                item_type=VocabularyItemType.VERB,
                base_verb="teilnehmen",
                preposition="an",
                grammatical_case="Dativ",
                example_german="Ich nehme morgen an einer Konferenz teil.",
                example_turkish="Yarın bir konferansa katılıyorum.",
            ),
        ],
        "Kapitel 2": [vocab("im Stau stehen", "trafikte kalmak", 2)],
    }
    upload = client.post(
        "/api/documents", files={"file": ("B1.pdf", make_pdf(BOOK), "application/pdf")}
    )
    document_id = upload.json()["id"]
    assert client.post(f"/api/documents/{document_id}/analyze").status_code == 200
    return document_id


def chapters_of(client: TestClient, document_id: int) -> list[dict]:
    response = client.get(f"/api/documents/{document_id}/chapters")
    assert response.status_code == 200
    return response.json()


def test_lists_chapters_in_order_with_vocabulary_counts(
    client: TestClient, fake_ai: FakeAIProvider
) -> None:
    chapters = chapters_of(client, analyzed_document(client, fake_ai))

    assert [
        (c["order"], c["chapter_number"], c["title"], c["source_start_page"], c["vocabulary_count"])
        for c in chapters
    ] == [(1, 1, "Kapitel 1", 1, 2), (2, 2, "Kapitel 2", 2, 1), (3, 3, "Kapitel 3", 3, 0)]
    assert set(chapters[0]) == {
        "id",
        "chapter_number",
        "title",
        "order",
        "source_start_page",
        "source_end_page",
        "vocabulary_count",
    }


def test_counts_match_the_analyze_response(client: TestClient, fake_ai: FakeAIProvider) -> None:
    document_id = analyzed_document(client, fake_ai)
    analysis = client.post(f"/api/documents/{document_id}/analyze", params={"force": True})

    assert chapters_of(client, document_id) == analysis.json()["chapters"]


def test_document_before_analysis_has_no_chapters(client: TestClient) -> None:
    upload = client.post(
        "/api/documents", files={"file": ("B1.pdf", make_pdf(BOOK), "application/pdf")}
    )

    assert chapters_of(client, upload.json()["id"]) == []


def test_chapters_of_unknown_document_is_404(client: TestClient) -> None:
    response = client.get("/api/documents/999/chapters")

    assert response.status_code == 404
    assert response.json()["error"]["details"] == {"document_id": 999}


def test_lists_vocabulary_of_a_chapter_in_pdf_order(
    client: TestClient, fake_ai: FakeAIProvider
) -> None:
    first_chapter = chapters_of(client, analyzed_document(client, fake_ai))[0]

    response = client.get(f"/api/chapters/{first_chapter['id']}/vocabulary")

    assert response.status_code == 200
    items = response.json()
    assert [(i["order"], i["german"], i["item_type"]) for i in items] == [
        (1, "die Veranstaltung", "noun"),
        (2, "an einer Konferenz teilnehmen", "verb"),
    ]
    verb = items[1]
    assert verb["chapter_id"] == first_chapter["id"]
    assert verb["turkish"] == "bir konferansa katılmak"
    assert (verb["base_verb"], verb["preposition"], verb["grammatical_case"]) == (
        "teilnehmen",
        "an",
        "Dativ",
    )
    assert verb["example_german"] == "Ich nehme morgen an einer Konferenz teil."
    assert verb["example_turkish"] == "Yarın bir konferansa katılıyorum."
    assert (verb["source_text"], verb["source_page"]) == ("an einer Konferenz teilnehmen", 1)
    assert items[0]["article"] == "die"


def test_chapter_without_vocabulary_returns_empty_list(
    client: TestClient, fake_ai: FakeAIProvider
) -> None:
    empty_chapter = chapters_of(client, analyzed_document(client, fake_ai))[2]

    assert client.get(f"/api/chapters/{empty_chapter['id']}/vocabulary").json() == []


def test_vocabulary_of_unknown_chapter_is_404(client: TestClient) -> None:
    response = client.get("/api/chapters/999/vocabulary")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "not_found",
        "message": "Chapter 999 was not found.",
        "details": {"chapter_id": 999},
    }
