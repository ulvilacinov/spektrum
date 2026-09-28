from typing import Any

from app.db.models import VocabularyItem
from app.domain.enums import QuestionType, VocabularyItemType
from app.services.learning import question_generation as qg


def item(german: str, turkish: str, **fields: Any) -> VocabularyItem:
    fields.setdefault("item_type", VocabularyItemType.PHRASE)
    return VocabularyItem(id=fields.pop("id", 1), german=german, turkish=turkish, order=1, **fields)


NOUN = item("die Veranstaltung", "etkinlik", item_type=VocabularyItemType.NOUN, article="die")
VERB = item(
    "an einer Konferenz teilnehmen",
    "bir konferansa katılmak",
    item_type=VocabularyItemType.VERB,
    base_verb="teilnehmen",
    prateritum="nahm teil",
    perfekt="hat teilgenommen",
    preposition="an",
    grammatical_case="Dativ",
    example_german="Ich nehme morgen an einer Konferenz teil.",
    example_turkish="Yarın bir konferansa katılıyorum.",
)


def test_translation_questions_in_both_directions() -> None:
    to_turkish = qg.german_to_turkish(NOUN)
    to_german = qg.turkish_to_german(NOUN)

    assert to_turkish.question_type is QuestionType.GERMAN_TO_TURKISH
    assert to_turkish.question == "„die Veranstaltung“ ifadesinin Türkçe karşılığı nedir?"
    assert to_turkish.expected_answer == "etkinlik"
    assert to_german.question == "„etkinlik“ Almanca nasıl söylenir?"
    assert to_german.expected_answer == "die Veranstaltung"


def test_article_question_hides_the_article() -> None:
    draft = qg.article(NOUN)

    assert draft.question == "Doğru artikeli yazın: ___ Veranstaltung — etkinlik"
    assert draft.expected_answer == "die"


def test_article_question_needs_a_plain_leading_article() -> None:
    assert qg.article(VERB) is None  # not a noun
    assert qg.article(item("Veranstaltung", "etkinlik", item_type=VocabularyItemType.NOUN)) is None
    odd = item("die Eltern", "ebeveynler", item_type=VocabularyItemType.NOUN, article="die (Pl.)")
    assert qg.article(odd) is None
    mismatch = item("der Tag", "gün", item_type=VocabularyItemType.NOUN, article="die")
    assert qg.article(mismatch) is None


def test_preposition_question_blanks_the_separate_word() -> None:
    draft = qg.preposition(VERB)

    assert draft.question == (
        "Boşluğa doğru edatı yazın: ___ einer Konferenz teilnehmen — bir konferansa katılmak"
    )
    assert draft.expected_answer == "an"


def test_preposition_inside_a_contraction_is_skipped() -> None:
    assert qg.preposition(item("im Stau stehen", "trafikte kalmak", preposition="in")) is None


def test_verb_conjugation_prefers_perfekt_then_prateritum() -> None:
    assert qg.verb_conjugation(VERB).expected_answer == "hat teilgenommen"
    only_past = item("stehen", "durmak", base_verb="stehen", prateritum="stand")
    draft = qg.verb_conjugation(only_past)
    assert draft.question == "„stehen“ fiilinin Präteritum hâli nedir? (er/sie/es)"
    assert draft.expected_answer == "stand"
    assert qg.verb_conjugation(item("stehen", "durmak", base_verb="stehen")) is None


def test_sentence_translation_uses_the_example_pair() -> None:
    draft = qg.sentence_translation(VERB)

    assert draft.question == "Bu cümleyi Almancaya çevirin: „Yarın bir konferansa katılıyorum.“"
    assert draft.expected_answer == "Ich nehme morgen an einer Konferenz teil."
    assert qg.sentence_translation(NOUN) is None


def test_one_question_per_item_in_order_and_reproducible() -> None:
    items = [item(f"Wort{n}", f"kelime{n}", id=n) for n in range(1, 21)]

    first = qg.generate_questions(items, seed=42)
    again = qg.generate_questions(items, seed=42)

    assert [q.vocabulary_item_id for q in first] == list(range(1, 21))
    assert first == again
    # Without extra data only the two translation directions are possible.
    assert {q.question_type for q in first} == {
        QuestionType.GERMAN_TO_TURKISH,
        QuestionType.TURKISH_TO_GERMAN,
    }


def test_rich_items_get_every_supported_question_type_over_many_seeds() -> None:
    types = {qg.generate_questions([VERB], seed=seed)[0].question_type for seed in range(100)}

    assert types == {
        QuestionType.GERMAN_TO_TURKISH,
        QuestionType.TURKISH_TO_GERMAN,
        QuestionType.PREPOSITION,
        QuestionType.VERB_CONJUGATION,
        QuestionType.SENTENCE_TRANSLATION,
    }


def test_repeated_preposition_is_blanked_everywhere() -> None:
    wait = item(
        "auf den Fahrstuhl/auf den Bus warten", "asansörü/otobüsü beklemek", preposition="auf"
    )

    draft = qg.preposition(wait)

    assert draft.question == (
        "Boşluğa doğru edatı yazın: ___ den Fahrstuhl/___ den Bus warten "
        "— asansörü/otobüsü beklemek"
    )
    assert draft.expected_answer == "auf"


def test_preposition_alone_is_not_a_question() -> None:
    assert qg.preposition(item("an", "-e", preposition="an")) is None


def test_perfekt_hint_does_not_suggest_only_haben() -> None:
    assert "ist gegangen" in qg.verb_conjugation(VERB).question


def test_sentence_translation_is_a_minority_even_for_rich_items() -> None:
    drafts = [qg.generate_questions([VERB], seed=seed)[0] for seed in range(1000)]
    share = sum(d.question_type is QuestionType.SENTENCE_TRANSLATION for d in drafts) / 1000

    assert 0.05 < share < 0.2  # weight 1 of 9 for this item


def test_article_question_skips_entries_with_several_nouns() -> None:
    pair = item(
        "die Backwaren, die Süßigkeiten",
        "unlu mamuller, tatlılar",
        item_type=VocabularyItemType.NOUN,
        article="die",
    )

    assert qg.article(pair) is None
