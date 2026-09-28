import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id
from app.db.models import (
    Chapter,
    Document,
    LearningSession,
    UserVocabularyProgress,
    VocabularyItem,
)
from app.domain.enums import DocumentStatus, VocabularyItemType, VocabularyStatus
from app.services.learning import new_progress

USER_ID = 1  # the test settings' default_user_id


@pytest.fixture
def chapter_id(sqlite_session: Session) -> int:
    """A parsed document with one chapter of 12 words (Wort1 … Wort12)."""
    chapter = Chapter(
        title="Kapitel 1", chapter_number=1, order=1, source_start_page=1, source_end_page=2
    )
    chapter.vocabulary_items = [
        VocabularyItem(
            german=f"Wort{n}",
            turkish=f"kelime{n}",
            item_type=VocabularyItemType.WORD,
            source_text=f"Wort{n}",
            source_page=1,
            order=n,
        )
        for n in range(1, 13)
    ]
    document = Document(
        file_name="a.pdf",
        original_file_name="B1.pdf",
        storage_path="a.pdf",
        status=DocumentStatus.PARSED,
        chapters=[chapter],
    )
    sqlite_session.add(document)
    sqlite_session.commit()
    return chapter.id


def start(client: TestClient, chapter_id: int, batch_size: int = 5):
    return client.post(
        "/api/learning-sessions", json={"chapter_id": chapter_id, "batch_size": batch_size}
    )


def item_words(client: TestClient, learning_session_id: int) -> list[str]:
    response = client.get(f"/api/learning-sessions/{learning_session_id}/items")
    assert response.status_code == 200
    return [item["vocabulary_item"]["german"] for item in response.json()]


def progress_of(sqlite_session: Session, german: str) -> UserVocabularyProgress | None:
    return sqlite_session.scalars(
        select(UserVocabularyProgress)
        .join(VocabularyItem, VocabularyItem.id == UserVocabularyProgress.vocabulary_item_id)
        .where(VocabularyItem.german == german)
    ).one_or_none()


def test_start_session_picks_the_first_batch_in_pdf_order(
    client: TestClient, sqlite_session: Session, chapter_id: int
) -> None:
    response = start(client, chapter_id, batch_size=5)

    assert response.status_code == 201
    body = response.json()
    assert (body["chapter_id"], body["batch_size"], body["item_count"]) == (chapter_id, 5, 5)
    assert body["started_at"] is not None
    assert (body["correct_count"], body["wrong_count"], body["completed_at"]) == (0, 0, None)
    assert item_words(client, body["id"]) == [f"Wort{n}" for n in range(1, 6)]
    assert sqlite_session.get(LearningSession, body["id"]).user_id == USER_ID


def test_studied_words_become_learning(
    client: TestClient, sqlite_session: Session, chapter_id: int
) -> None:
    session_id = start(client, chapter_id).json()["id"]

    items = client.get(f"/api/learning-sessions/{session_id}/items").json()

    assert {item["status"] for item in items} == {"learning"}
    assert [item["position"] for item in items] == [1, 2, 3, 4, 5]
    progress = progress_of(sqlite_session, "Wort1")
    assert (progress.user_id, progress.status, progress.seen_count) == (
        USER_ID,
        VocabularyStatus.LEARNING,
        1,
    )
    assert progress.last_seen_at is not None
    assert progress_of(sqlite_session, "Wort6") is None


def test_next_sessions_continue_with_the_next_batch_until_the_chapter_is_done(
    client: TestClient, chapter_id: int
) -> None:
    first = start(client, chapter_id, 5).json()
    second = start(client, chapter_id, 5).json()
    last = start(client, chapter_id, 5).json()

    assert item_words(client, first["id"])[0] == "Wort1"
    assert item_words(client, second["id"]) == [f"Wort{n}" for n in range(6, 11)]
    assert item_words(client, last["id"]) == ["Wort11", "Wort12"]
    assert (last["batch_size"], last["item_count"]) == (5, 2)

    finished = start(client, chapter_id, 5)
    assert finished.status_code == 409
    assert finished.json()["error"]["code"] == "no_new_vocabulary"


def test_items_already_in_progress_are_not_picked_again(
    client: TestClient, sqlite_session: Session, chapter_id: int
) -> None:
    items = sqlite_session.scalars(
        select(VocabularyItem).where(VocabularyItem.chapter_id == chapter_id)
    ).all()
    by_word = {item.german: item for item in items}
    weak = new_progress(USER_ID, by_word["Wort1"].id)
    weak.status = VocabularyStatus.WEAK
    untouched = new_progress(USER_ID, by_word["Wort2"].id)  # exists but still "new"
    sqlite_session.add_all([weak, untouched])
    sqlite_session.commit()

    session_id = start(client, chapter_id, 5).json()["id"]

    assert item_words(client, session_id) == ["Wort2", "Wort3", "Wort4", "Wort5", "Wort6"]
    assert progress_of(sqlite_session, "Wort2").status is VocabularyStatus.LEARNING
    assert progress_of(sqlite_session, "Wort1").status is VocabularyStatus.WEAK


@pytest.mark.parametrize("batch_size", [1, 3, 7])
def test_any_batch_size_is_accepted(client: TestClient, chapter_id: int, batch_size: int) -> None:
    body = start(client, chapter_id, batch_size).json()

    assert (body["batch_size"], body["item_count"]) == (batch_size, batch_size)
    assert item_words(client, body["id"]) == [f"Wort{n}" for n in range(1, batch_size + 1)]


def test_batch_size_defaults_to_10(client: TestClient, chapter_id: int) -> None:
    response = client.post("/api/learning-sessions", json={"chapter_id": chapter_id})

    assert response.status_code == 201
    assert (response.json()["batch_size"], response.json()["item_count"]) == (10, 10)


@pytest.mark.parametrize("batch_size", [0, -5, 101])
def test_batch_size_must_be_between_1_and_100(
    client: TestClient, chapter_id: int, batch_size: int
) -> None:
    assert start(client, chapter_id, batch_size).status_code == 422


def test_batch_of_20_takes_what_is_left(client: TestClient, chapter_id: int) -> None:
    body = start(client, chapter_id, 20).json()

    assert (body["batch_size"], body["item_count"]) == (20, 12)


def test_unknown_chapter_is_404(client: TestClient) -> None:
    response = start(client, 999)

    assert response.status_code == 404
    assert response.json()["error"]["details"] == {"chapter_id": 999}


def test_unknown_session_is_404(client: TestClient) -> None:
    response = client.get("/api/learning-sessions/999/items")

    assert response.status_code == 404
    assert response.json()["error"]["details"] == {"learning_session_id": 999}


def test_sessions_and_progress_are_per_user(client: TestClient, chapter_id: int) -> None:
    session_id = start(client, chapter_id).json()["id"]
    client.app.dependency_overrides[get_current_user_id] = lambda: 2

    assert client.get(f"/api/learning-sessions/{session_id}/items").status_code == 404
    other = start(client, chapter_id).json()
    assert item_words(client, other["id"])[0] == "Wort1"  # user 2 starts from the beginning
