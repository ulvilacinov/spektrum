from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_ai_provider_factory, get_current_user_id
from app.db.models import (
    Chapter,
    Document,
    LearningSession,
    QuizQuestion,
    UserVocabularyProgress,
    VocabularyItem,
)
from app.domain.enums import DocumentStatus, QuestionType, VocabularyItemType, VocabularyStatus
from app.services.ai import AINotConfiguredError, AIProviderError
from app.services.ai.schemas import AnswerEvaluationResult
from tests.fake_ai import FakeAIProvider

NOUN = ("die Veranstaltung", "etkinlik")
VERB = ("an einer Konferenz teilnehmen", "bir konferansa katılmak")
TRAFFIC = ("im Stau stehen", "Trafikte kalmak/beklemek")


@pytest.fixture
def questions(client: TestClient, sqlite_session: Session) -> dict[str, int]:
    """A 3-word session with one quiz question per word; returns question ids by name."""
    chapter = Chapter(
        title="Kapitel 1", chapter_number=1, order=1, source_start_page=1, source_end_page=1
    )
    chapter.vocabulary_items = [
        VocabularyItem(
            german=NOUN[0],
            turkish=NOUN[1],
            item_type=VocabularyItemType.NOUN,
            article="die",
            order=1,
        ),
        VocabularyItem(
            german=VERB[0],
            turkish=VERB[1],
            item_type=VocabularyItemType.VERB,
            example_german="Ich nehme morgen an einer Konferenz teil.",
            example_turkish="Yarın bir konferansa katılıyorum.",
            order=2,
        ),
        VocabularyItem(
            german=TRAFFIC[0], turkish=TRAFFIC[1], item_type=VocabularyItemType.PHRASE, order=3
        ),
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
    session_id = client.post(
        "/api/learning-sessions", json={"chapter_id": chapter.id, "batch_size": 3}
    ).json()["id"]

    noun, verb, traffic = chapter.vocabulary_items
    specs = {
        "article": (noun, QuestionType.ARTICLE, "Doğru artikeli yazın: ___ Veranstaltung", "die"),
        "sentence": (
            verb,
            QuestionType.SENTENCE_TRANSLATION,
            "Bu cümleyi Almancaya çevirin: „Yarın bir konferansa katılıyorum.“",
            "Ich nehme morgen an einer Konferenz teil.",
        ),
        "to_turkish": (
            traffic,
            QuestionType.GERMAN_TO_TURKISH,
            "„im Stau stehen“ ifadesinin Türkçe karşılığı nedir?",
            TRAFFIC[1],
        ),
    }
    ids = {}
    for position, (name, (item, question_type, text, expected)) in enumerate(
        specs.items(), start=1
    ):
        question = QuizQuestion(
            learning_session_id=session_id,
            vocabulary_item_id=item.id,
            position=position,
            question_type=question_type,
            question=text,
            expected_answer=expected,
        )
        sqlite_session.add(question)
        sqlite_session.flush()
        ids[name] = question.id
    sqlite_session.commit()
    return ids


def answer(client: TestClient, question_id: int, text: str):
    return client.post(f"/api/quiz/{question_id}/answer", json={"answer": text})


def progress_of(sqlite_session: Session, german: str) -> UserVocabularyProgress:
    sqlite_session.expire_all()
    return sqlite_session.scalars(
        select(UserVocabularyProgress)
        .join(VocabularyItem, VocabularyItem.id == UserVocabularyProgress.vocabulary_item_id)
        .where(VocabularyItem.german == german)
    ).one()


def test_exact_answer_is_correct_without_ai(
    client: TestClient, questions: dict[str, int], fake_ai: FakeAIProvider
) -> None:
    response = answer(client, questions["article"], "die")

    assert response.status_code == 200
    body = response.json()
    question = body["question"]
    assert (question["is_correct"], question["score"], question["evaluation_method"]) == (
        True,
        1.0,
        "exact",
    )
    assert question["ai_feedback"] == "Doğru!"
    assert (question["user_answer"], question["expected_answer"]) == ("die", "die")
    assert question["error_type"] is None
    assert question["answered_at"] is not None
    assert body["vocabulary_status"] == "learning"
    assert (body["learning_session"]["correct_count"], body["learning_session"]["wrong_count"]) == (
        1,
        0,
    )
    assert fake_ai.evaluation_calls == []


def test_alternative_without_turkish_letters_is_correct_after_normalization(
    client: TestClient, questions: dict[str, int], fake_ai: FakeAIProvider
) -> None:
    question = answer(client, questions["to_turkish"], "trafikte beklemek").json()["question"]

    assert (question["is_correct"], question["evaluation_method"]) == (True, "normalized")
    assert question["ai_feedback"] == "Doğru! Kitaptaki yazılışı: „Trafikte kalmak/beklemek“."
    assert fake_ai.evaluation_calls == []


def test_wrong_closed_answer_is_judged_by_rule_and_makes_the_word_weak(
    client: TestClient, questions: dict[str, int], sqlite_session: Session, fake_ai: FakeAIProvider
) -> None:
    body = answer(client, questions["article"], "der").json()

    question = body["question"]
    assert (question["is_correct"], question["evaluation_method"], question["error_type"]) == (
        False,
        "rule",
        "article",
    )
    assert question["ai_feedback"] == "Yanlış. Doğru artikel „die“: die Veranstaltung."
    assert body["vocabulary_status"] == "weak"
    progress = progress_of(sqlite_session, NOUN[0])
    assert (progress.wrong_count, progress.next_review_at is not None) == (1, True)
    assert fake_ai.evaluation_calls == []


def test_open_answer_that_does_not_match_goes_to_the_ai(
    client: TestClient, questions: dict[str, int], fake_ai: FakeAIProvider
) -> None:
    fake_ai.evaluation = AnswerEvaluationResult(
        is_correct=False,
        score=0.75,
        corrected_answer="Ich nehme morgen an einer Konferenz teil.",
        explanation="'teilnehmen' ayrılabilen bir fiildir: 'nehme … teil'.",
        error_type="verb_conjugation",
    )

    question = answer(client, questions["sentence"], "Ich teilnehme morgen an einer Konferenz.")
    question = question.json()["question"]

    assert (question["is_correct"], question["score"], question["evaluation_method"]) == (
        False,
        0.75,
        "ai",
    )
    assert question["error_type"] == "verb_conjugation"
    assert question["ai_feedback"] == "'teilnehmen' ayrılabilen bir fiildir: 'nehme … teil'."
    assert question["corrected_answer"] == "Ich nehme morgen an einer Konferenz teil."
    [request] = fake_ai.evaluation_calls
    assert request.question_type is QuestionType.SENTENCE_TRANSLATION
    assert request.user_answer == "Ich teilnehme morgen an einer Konferenz."
    assert request.expected_answer == "Ich nehme morgen an einer Konferenz teil."
    assert (request.answer_language, request.german) == ("German", VERB[0])


def test_ai_can_accept_an_answer_that_differs_from_the_book(
    client: TestClient, questions: dict[str, int], fake_ai: FakeAIProvider
) -> None:
    fake_ai.evaluation = AnswerEvaluationResult(
        is_correct=True, score=1.0, explanation="Doğru!", error_type="grammar"
    )

    body = answer(client, questions["sentence"], "Morgen nehme ich an einer Konferenz teil.").json()

    assert body["question"]["is_correct"] is True
    assert body["question"]["error_type"] is None  # never an error type for correct answers
    assert body["question"]["corrected_answer"] == "Ich nehme morgen an einer Konferenz teil."
    assert body["vocabulary_status"] == "learning"


def test_second_correct_answer_in_a_row_masters_the_word(
    client: TestClient, questions: dict[str, int], sqlite_session: Session
) -> None:
    progress = progress_of(sqlite_session, NOUN[0])
    progress.consecutive_correct = 1  # answered correctly in an earlier quiz
    sqlite_session.commit()

    body = answer(client, questions["article"], "die").json()

    assert body["vocabulary_status"] == "mastered"
    assert progress_of(sqlite_session, NOUN[0]).mastery_score == 1.0


def test_session_completes_when_every_question_is_answered(
    client: TestClient, questions: dict[str, int]
) -> None:
    answer(client, questions["article"], "die")
    answer(client, questions["to_turkish"], "trafikte kalmak")
    body = answer(client, questions["sentence"], "falsch").json()

    session = body["learning_session"]
    assert (session["correct_count"], session["wrong_count"]) == (2, 1)
    assert session["completed_at"] is not None


def test_session_is_not_complete_while_questions_are_open(
    client: TestClient, questions: dict[str, int]
) -> None:
    body = answer(client, questions["article"], "die").json()

    assert body["learning_session"]["completed_at"] is None


def test_a_question_can_only_be_answered_once(
    client: TestClient, questions: dict[str, int], sqlite_session: Session
) -> None:
    answer(client, questions["article"], "der")

    again = answer(client, questions["article"], "die")

    assert again.status_code == 409
    assert again.json()["error"]["code"] == "question_already_answered"
    assert progress_of(sqlite_session, NOUN[0]).wrong_count == 1


def test_quiz_reveals_expected_answers_only_for_answered_questions(
    client: TestClient, questions: dict[str, int], sqlite_session: Session
) -> None:
    answer(client, questions["article"], "die")
    session_id = sqlite_session.scalars(select(LearningSession.id)).one()

    quiz = client.post(f"/api/learning-sessions/{session_id}/quiz").json()["questions"]

    assert [q["expected_answer"] for q in quiz] == ["die", None, None]


def test_failed_ai_call_leaves_the_question_open_for_a_retry(
    client: TestClient, questions: dict[str, int], sqlite_session: Session, fake_ai: FakeAIProvider
) -> None:
    fake_ai.error = AIProviderError("The AI service request failed.")

    failed = answer(client, questions["sentence"], "Ich weiß es nicht.")

    assert failed.status_code == 502
    assert sqlite_session.get(QuizQuestion, questions["sentence"]).user_answer is None
    assert progress_of(sqlite_session, VERB[0]).wrong_count == 0

    fake_ai.error = None
    assert answer(client, questions["sentence"], "Ich weiß es nicht.").status_code == 200


def test_deterministic_answers_work_without_ai_configuration(
    client: TestClient, questions: dict[str, int]
) -> None:
    def not_configured() -> Callable[[], None]:
        def factory() -> None:
            raise AINotConfiguredError("GEMINI_API_KEY is not set.")

        return factory

    client.app.dependency_overrides[get_ai_provider_factory] = not_configured

    assert answer(client, questions["article"], "die").status_code == 200
    assert answer(client, questions["to_turkish"], "trafikte kalmak").status_code == 200
    assert answer(client, questions["sentence"], "etwas anderes").status_code == 503


@pytest.mark.parametrize("text", ["", "   "])
def test_blank_answers_are_rejected(
    client: TestClient, questions: dict[str, int], text: str
) -> None:
    assert answer(client, questions["article"], text).status_code == 422


def test_answer_is_stored_trimmed(
    client: TestClient, questions: dict[str, int], sqlite_session: Session
) -> None:
    answer(client, questions["article"], "  die  ")

    assert sqlite_session.get(QuizQuestion, questions["article"]).user_answer == "die"


def test_unknown_question_is_404(client: TestClient) -> None:
    response = answer(client, 999, "die")

    assert response.status_code == 404
    assert response.json()["error"]["details"] == {"question_id": 999}


def test_other_users_question_is_404(client: TestClient, questions: dict[str, int]) -> None:
    client.app.dependency_overrides[get_current_user_id] = lambda: 2

    assert answer(client, questions["article"], "die").status_code == 404


def test_progress_without_a_record_is_created(
    client: TestClient, questions: dict[str, int], sqlite_session: Session
) -> None:
    sqlite_session.delete(progress_of(sqlite_session, NOUN[0]))
    sqlite_session.commit()

    body = answer(client, questions["article"], "die").json()

    assert body["vocabulary_status"] == VocabularyStatus.LEARNING
    assert progress_of(sqlite_session, NOUN[0]).correct_count == 1
