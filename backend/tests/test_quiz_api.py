import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id
from app.db.models import Chapter, Document, QuizQuestion, VocabularyItem
from app.domain.enums import DocumentStatus, VocabularyItemType


@pytest.fixture
def learning_session_id(client: TestClient, sqlite_session: Session) -> int:
    """A started 5-word session of a chapter with 7 words (Wort1 … Wort7)."""
    chapter = Chapter(
        title="Kapitel 1", chapter_number=1, order=1, source_start_page=1, source_end_page=1
    )
    chapter.vocabulary_items = [
        VocabularyItem(
            german=f"Wort{n}", turkish=f"kelime{n}", item_type=VocabularyItemType.WORD, order=n
        )
        for n in range(1, 8)
    ]
    sqlite_session.add(
        Document(
            user_id=1,
            file_name="a.pdf",
            original_file_name="B1.pdf",
            storage_path="a.pdf",
            status=DocumentStatus.PARSED,
            chapters=[chapter],
        )
    )
    sqlite_session.commit()
    response = client.post(
        "/api/learning-sessions", json={"chapter_id": chapter.id, "batch_size": 5}
    )
    return response.json()["id"]


def create_quiz(client: TestClient, learning_session_id: int):
    return client.post(f"/api/learning-sessions/{learning_session_id}/quiz")


def test_quiz_has_one_question_per_session_word(
    client: TestClient, learning_session_id: int
) -> None:
    response = create_quiz(client, learning_session_id)

    assert response.status_code == 201
    body = response.json()
    assert (body["learning_session_id"], body["question_count"]) == (learning_session_id, 5)
    questions = body["questions"]
    assert [q["position"] for q in questions] == [1, 2, 3, 4, 5]
    session_items = client.get(f"/api/learning-sessions/{learning_session_id}/items").json()
    assert [q["vocabulary_item_id"] for q in questions] == [
        item["vocabulary_item"]["id"] for item in session_items
    ]
    assert {q["question_type"] for q in questions} <= {"german_to_turkish", "turkish_to_german"}
    assert all(q["user_answer"] is None and q["is_correct"] is None for q in questions)


def test_expected_answers_are_not_exposed(
    client: TestClient, sqlite_session: Session, learning_session_id: int
) -> None:
    questions = create_quiz(client, learning_session_id).json()["questions"]

    assert all(q["expected_answer"] is None for q in questions)  # revealed after answering
    stored = sqlite_session.scalars(select(QuizQuestion).order_by(QuizQuestion.position)).all()
    for question in stored:
        word = sqlite_session.get(VocabularyItem, question.vocabulary_item_id)
        expected = word.turkish if question.question_type == "german_to_turkish" else word.german
        assert question.expected_answer == expected


def test_calling_again_returns_the_same_quiz(
    client: TestClient, sqlite_session: Session, learning_session_id: int
) -> None:
    first = create_quiz(client, learning_session_id)
    second = create_quiz(client, learning_session_id)

    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json() == first.json()
    assert len(sqlite_session.scalars(select(QuizQuestion)).all()) == 5


def test_quiz_of_unknown_session_is_404(client: TestClient) -> None:
    response = create_quiz(client, 999)

    assert response.status_code == 404
    assert response.json()["error"]["details"] == {"learning_session_id": 999}


def test_quiz_of_another_users_session_is_404(client: TestClient, learning_session_id: int) -> None:
    client.app.dependency_overrides[get_current_user_id] = lambda: 2

    assert create_quiz(client, learning_session_id).status_code == 404
