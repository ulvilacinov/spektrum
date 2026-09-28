import pytest

from app.domain.enums import EvaluationMethod
from app.services.learning.answer_matching import (
    Language,
    expected_variants,
    match_answer,
    normalize,
)

DE, TR = Language.GERMAN, Language.TURKISH
EXACT, NORMALIZED = EvaluationMethod.EXACT, EvaluationMethod.NORMALIZED


def test_exact_match() -> None:
    assert match_answer("die Veranstaltung", "die Veranstaltung", DE) is EXACT
    assert match_answer("  die Veranstaltung ", "die Veranstaltung", DE) is EXACT


@pytest.mark.parametrize(
    "answer",
    ["Die Veranstaltung", "die  veranstaltung", "die Veranstaltung.", "„die Veranstaltung“"],
)
def test_case_whitespace_and_punctuation_are_ignored(answer: str) -> None:
    assert match_answer(answer, "die Veranstaltung", DE) is NORMALIZED


def test_german_keyboard_spellings_are_accepted_but_umlauts_matter() -> None:
    assert match_answer("die Groesse", "die Größe", DE) is NORMALIZED
    assert match_answer("Strasse", "Straße", DE) is NORMALIZED
    assert match_answer("schon", "schön", DE) is None


def test_turkish_letters_may_be_typed_without_diacritics() -> None:
    assert match_answer("arkadaslar ile bulusmak", "Arkadaşlar ile buluşmak", TR) is NORMALIZED
    assert match_answer("IŞIK", "ışık", TR) is NORMALIZED
    assert normalize("İstanbul", TR) == "istanbul"


def test_word_alternatives() -> None:
    expected = "Trafikte kalmak/beklemek"

    assert match_answer("trafikte kalmak", expected, TR) is NORMALIZED
    assert match_answer("trafikte beklemek", expected, TR) is NORMALIZED
    assert match_answer("beklemek", expected, TR) is None  # half an answer is not enough


def test_whole_phrase_alternatives() -> None:
    expected = "Mich nervt es/Ich mag es nicht"

    assert match_answer("Ich mag es nicht", expected, DE) is NORMALIZED
    assert match_answer("mich nervt es", expected, DE) is NORMALIZED


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("an ein tolles Konzert denken", "an (ein tolles Konzert) denken"),
        ("an denken", "an (ein tolles Konzert) denken"),
        ("die Wohnung aufräumen", "(die Wohnung) aufräumen/sauber machen"),
        ("sauber machen", "(die Wohnung) aufräumen/sauber machen"),
        ("präsentieren", "(Ergebnisse/Projekte) präsentieren"),
        ("Projekte präsentieren", "(Ergebnisse/Projekte) präsentieren"),
        ("Einer Studie zufolge", "Einer Umfrage/Studie zufolge …"),
        ("E-Mails beantworten", "E-Mails checken/schreiben/beantworten"),
    ],
)
def test_optional_parts_and_alternatives_from_the_real_book(answer: str, expected: str) -> None:
    assert match_answer(answer, expected, DE) is NORMALIZED


def test_wrong_answers_are_not_matched() -> None:
    assert match_answer("der Veranstaltung", "die Veranstaltung", DE) is None
    assert match_answer("", "die Veranstaltung", DE) is None
    assert match_answer("...", "die Veranstaltung", DE) is None


def test_variant_explosion_is_capped() -> None:
    expected = " ".join(["a/b/c"] * 10)  # 3**10 combinations

    assert len(expected_variants(expected)) <= 4 * 64
