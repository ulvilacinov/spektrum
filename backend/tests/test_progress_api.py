import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id
from app.db.models import Chapter, Document, QuizQuestion, VocabularyItem
from app.domain.enums import DocumentStatus, VocabularyItemType

WORDS = ["Wort1", "Wort2", "Wort3", "Wort4"]


@pytest.fixture
def ids(sqlite_session: Session) -> dict[str, int]:
    """A parsed document with a 4-word chapter and an empty chapter."""
    chapter = Chapter(
        title="Kapitel 1", chapter_number=1, order=1, source_start_page=1, source_end_page=1
    )
    chapter.vocabulary_items = [
        VocabularyItem(
            german=word,
            turkish=f"kelime{n}",
            item_type=VocabularyItemType.WORD,
            order=n,
        )
        for n, word in enumerate(WORDS, start=1)
    ]
    empty = Chapter(
        title="Kapitel 2", chapter_number=2, order=2, source_start_page=2, source_end_page=2
    )
    document = Document(
        user_id=1,
        file_name="a.pdf",
        original_file_name="B1.pdf",
        storage_path="a.pdf",
        status=DocumentStatus.PARSED,
        chapters=[chapter, empty],
    )
    sqlite_session.add(document)
    sqlite_session.commit()
    return {"document": document.id, "chapter": chapter.id, "empty": empty.id}


def start(client: TestClient, chapter_id: int, batch_size: int = 2, mode: str = "new"):
    return client.post(
        "/api/learning-sessions",
        json={"chapter_id": chapter_id, "batch_size": batch_size, "mode": mode},
    )


def quiz_and_answer(
    client: TestClient, sqlite_session: Session, session_id: int, wrong: set[str] = frozenset()
) -> list[str]:
    """Create the session's quiz and answer it; words in ``wrong`` get a wrong answer."""
    questions = client.post(f"/api/learning-sessions/{session_id}/quiz").json()["questions"]
    words = []
    for question in questions:
        stored = sqlite_session.get(QuizQuestion, question["id"])
        word = sqlite_session.get(VocabularyItem, stored.vocabulary_item_id).german
        words.append(word)
        # Correct answers match exactly; wrong ones go to the fake AI, which rejects them.
        text = stored.expected_answer if word not in wrong else "falsch"
        response = client.post(f"/api/quiz/{question['id']}/answer", json={"answer": text})
        assert response.status_code == 200, response.json()
    return words


def progress(client: TestClient, document_id: int) -> dict:
    response = client.get("/api/progress", params={"document_id": document_id})
    assert response.status_code == 200
    return response.json()


def statuses(chapter: dict) -> tuple[int, int, int, int]:
    return chapter["new"], chapter["learning"], chapter["weak"], chapter["mastered"]


def test_full_learning_cycle_learn_quiz_weak_review_master_next_batch(
    client: TestClient, sqlite_session: Session, ids: dict[str, int]
) -> None:
    chapter_id = ids["chapter"]

    # 1. Learn the first batch and take its quiz: Wort2 is answered wrongly.
    first = start(client, chapter_id).json()
    assert quiz_and_answer(client, sqlite_session, first["id"], wrong={"Wort2"}) == [
        "Wort1",
        "Wort2",
    ]
    chapter = progress(client, ids["document"])["chapters"][0]
    assert statuses(chapter) == (2, 1, 1, 0)
    assert (chapter["can_start_new_batch"], chapter["can_review"]) == (False, True)

    # 2. The next batch is locked until the studied words are mastered.
    locked = start(client, chapter_id)
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "batch_locked"
    assert locked.json()["error"]["details"] == {
        "chapter_id": chapter_id,
        "learning": 1,
        "weak": 1,
    }

    # 3. Weak words are listed with the mistake that made them weak.
    [weak] = client.get("/api/review/weak", params={"chapter_id": chapter_id}).json()
    assert weak["vocabulary_item"]["german"] == "Wort2"
    assert weak["progress"]["wrong_count"] == 1
    assert weak["last_mistake"]["user_answer"] == "falsch"
    assert weak["last_mistake"]["feedback"]

    # 4. A review session puts the weak word first; both answered correctly.
    review = start(client, chapter_id, batch_size=10, mode="review").json()
    assert (review["mode"], review["item_count"]) == ("review", 2)
    assert quiz_and_answer(client, sqlite_session, review["id"]) == ["Wort2", "Wort1"]
    chapter = progress(client, ids["document"])["chapters"][0]
    assert statuses(chapter) == (2, 1, 0, 1)  # Wort1: 2 in a row → mastered; Wort2: learning
    assert client.get("/api/review/weak").json() == []

    # 5. One more correct review answer masters Wort2 and unlocks the next batch.
    again = start(client, chapter_id, mode="review").json()
    assert quiz_and_answer(client, sqlite_session, again["id"]) == ["Wort2"]
    chapter = progress(client, ids["document"])["chapters"][0]
    assert statuses(chapter) == (2, 0, 0, 2)
    assert (chapter["can_start_new_batch"], chapter["can_review"]) == (True, False)
    assert chapter["mastery_ratio"] == 0.5

    next_batch = start(client, chapter_id)
    assert next_batch.status_code == 201
    words = client.get(f"/api/learning-sessions/{next_batch.json()['id']}/items").json()
    assert [w["vocabulary_item"]["german"] for w in words] == ["Wort3", "Wort4"]


def test_progress_lists_every_chapter_with_totals(client: TestClient, ids: dict[str, int]) -> None:
    start(client, ids["chapter"], batch_size=3)

    body = progress(client, ids["document"])

    assert (body["total"], body["new"], body["learning"], body["mastered"]) == (4, 1, 3, 0)
    first, empty = body["chapters"]
    assert (first["chapter_id"], first["title"], first["total"]) == (ids["chapter"], "Kapitel 1", 4)
    assert (empty["chapter_id"], empty["total"], empty["mastery_ratio"]) == (ids["empty"], 0, 0.0)
    assert (empty["can_start_new_batch"], empty["can_review"]) == (False, False)


def test_progress_before_studying_is_all_new(client: TestClient, ids: dict[str, int]) -> None:
    chapter = progress(client, ids["document"])["chapters"][0]

    assert statuses(chapter) == (4, 0, 0, 0)
    assert chapter["can_start_new_batch"] is True


def test_progress_without_document_filter_covers_all_documents(
    client: TestClient, ids: dict[str, int]
) -> None:
    body = client.get("/api/progress").json()

    assert [c["chapter_id"] for c in body["chapters"]] == [ids["chapter"], ids["empty"]]


def test_progress_of_another_users_document_is_not_found(
    client: TestClient, ids: dict[str, int]
) -> None:
    start(client, ids["chapter"], batch_size=3)
    client.app.dependency_overrides[get_current_user_id] = lambda: 2

    assert client.get("/api/progress", params={"document_id": ids["document"]}).status_code == 404
    assert client.get("/api/progress").json()["chapters"] == []
    assert client.get("/api/review/weak").json() == []


def test_review_needs_studied_words(client: TestClient, ids: dict[str, int]) -> None:
    response = start(client, ids["chapter"], mode="review")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "nothing_to_review"


def test_review_can_come_before_the_quiz(client: TestClient, ids: dict[str, int]) -> None:
    start(client, ids["chapter"], batch_size=2)

    review = start(client, ids["chapter"], batch_size=5, mode="review")

    assert review.status_code == 201
    assert review.json()["item_count"] == 2


def test_unknown_mode_is_rejected(client: TestClient, ids: dict[str, int]) -> None:
    assert start(client, ids["chapter"], mode="random").status_code == 422


def test_unknown_filters_are_404(client: TestClient) -> None:
    assert client.get("/api/progress", params={"document_id": 999}).status_code == 404
    assert client.get("/api/review/weak", params={"document_id": 999}).status_code == 404
    assert client.get("/api/review/weak", params={"chapter_id": 999}).status_code == 404


def test_weak_words_are_per_user(
    client: TestClient, sqlite_session: Session, ids: dict[str, int]
) -> None:
    session_id = start(client, ids["chapter"]).json()["id"]
    quiz_and_answer(client, sqlite_session, session_id, wrong={"Wort1", "Wort2"})

    assert len(client.get("/api/review/weak").json()) == 2
    client.app.dependency_overrides[get_current_user_id] = lambda: 2
    assert client.get("/api/review/weak").json() == []
