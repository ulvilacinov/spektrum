"""Builds quiz questions from the data stored for each vocabulary item. No AI involved.

Every question's expected answer comes straight from the item's stored fields, which in
turn originate from the PDF (translations/examples may be AI-generated during analysis).
Question texts are in Turkish because they are learner-facing.
"""

import random
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.db.models import VocabularyItem
from app.domain.enums import QuestionType, VocabularyItemType

ARTICLES = ("der", "die", "das")


@dataclass(frozen=True, slots=True)
class QuestionDraft:
    vocabulary_item_id: int
    question_type: QuestionType
    question: str
    expected_answer: str


def german_to_turkish(item: VocabularyItem) -> QuestionDraft:
    return _draft(
        item,
        QuestionType.GERMAN_TO_TURKISH,
        f"„{item.german}“ ifadesinin Türkçe karşılığı nedir?",
        item.turkish,
    )


def turkish_to_german(item: VocabularyItem) -> QuestionDraft:
    return _draft(
        item,
        QuestionType.TURKISH_TO_GERMAN,
        f"„{item.turkish}“ Almanca nasıl söylenir?",
        item.german,
    )


def article(item: VocabularyItem) -> QuestionDraft | None:
    """Only for nouns stored as "<article> <noun>" with a plain der/die/das article."""
    if item.item_type is not VocabularyItemType.NOUN or not item.article:
        return None
    stored_article = item.article.strip().lower()
    first, _, rest = item.german.partition(" ")
    if stored_article not in ARTICLES or first.lower() != stored_article or not rest:
        return None
    # "die Backwaren, die Süßigkeiten": a second article would give the answer away.
    if any(word.lower().strip(",;/()") in ARTICLES for word in rest.split()):
        return None
    return _draft(
        item,
        QuestionType.ARTICLE,
        f"Doğru artikeli yazın: ___ {rest} — {item.turkish}",
        stored_article,
    )


def preposition(item: VocabularyItem) -> QuestionDraft | None:
    """Blanks every occurrence of the preposition as a separate word.

    "auf den Fahrstuhl/auf den Bus warten" → "___ den Fahrstuhl/___ den Bus warten"; a
    preposition only inside a contraction ("im" = in dem) is not asked.
    """
    target = (item.preposition or "").strip()
    if not target:
        return None
    word = re.compile(rf"(?<!\w){re.escape(target)}(?!\w)", re.IGNORECASE)
    match = word.search(item.german)
    blanked = word.sub("___", item.german)
    if match is None or not blanked.replace("___", "").strip():
        return None
    return _draft(
        item,
        QuestionType.PREPOSITION,
        f"Boşluğa doğru edatı yazın: {blanked} — {item.turkish}",
        match.group(0),
    )


def verb_conjugation(item: VocabularyItem) -> QuestionDraft | None:
    verb = item.base_verb
    if not verb:
        return None
    if item.perfekt:
        return _draft(
            item,
            QuestionType.VERB_CONJUGATION,
            f"„{verb}“ fiilinin Perfekt hâli nedir? (yardımcı fiille: ör. „hat gemacht“, "
            "„ist gegangen“)",
            item.perfekt,
        )
    if item.prateritum:
        return _draft(
            item,
            QuestionType.VERB_CONJUGATION,
            f"„{verb}“ fiilinin Präteritum hâli nedir? (er/sie/es)",
            item.prateritum,
        )
    return None


def sentence_translation(item: VocabularyItem) -> QuestionDraft | None:
    if not item.example_german or not item.example_turkish:
        return None
    return _draft(
        item,
        QuestionType.SENTENCE_TRANSLATION,
        f"Bu cümleyi Almancaya çevirin: „{item.example_turkish}“",
        item.example_german,
    )


QuestionBuilder = Callable[[VocabularyItem], QuestionDraft | None]

# (builder, weight). Every item supports the two translation directions; the others need
# specific data. Questions about the item itself are favoured over whole-sentence
# translation, which is harder and will usually need AI evaluation.
BUILDERS: tuple[tuple[QuestionBuilder, int], ...] = (
    (german_to_turkish, 2),
    (turkish_to_german, 3),
    (article, 2),
    (preposition, 2),
    (verb_conjugation, 1),
    (sentence_translation, 1),
)


def generate_questions(
    items: Sequence[VocabularyItem],
    *,
    seed: int,
    builders: Sequence[tuple[QuestionBuilder, int]] = BUILDERS,
) -> list[QuestionDraft]:
    """One question per item, its type drawn (weighted) from the types its data supports.

    ``seed`` (the learning session id) makes a session's quiz reproducible.
    """
    rng = random.Random(seed)
    questions = []
    for item in items:
        candidates = [
            (draft, weight) for build, weight in builders if (draft := build(item)) is not None
        ]
        drafts, weights = zip(*candidates, strict=True)
        questions.append(rng.choices(drafts, weights=weights)[0])
    return questions


def _draft(
    item: VocabularyItem, question_type: QuestionType, question: str, expected_answer: str
) -> QuestionDraft:
    return QuestionDraft(
        vocabulary_item_id=item.id,
        question_type=question_type,
        question=question,
        expected_answer=expected_answer,
    )
