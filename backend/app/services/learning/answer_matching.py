"""Deterministic answer checking: exact match, then normalized comparison.

Expected answers come from vocabulary books and look like "Trafikte kalmak/beklemek" or
"an (ein tolles Konzert) denken": "/" separates alternatives and parentheses mark optional
or example parts. ``expected_variants`` expands such an answer into every accepted form.
"""

import itertools
import re
import unicodedata
from enum import StrEnum

from app.domain.enums import EvaluationMethod

MAX_VARIANTS = 64

_PUNCTUATION = str.maketrans(
    {char: " " for char in ".,;:!?\"'„“”‚‘’«»…()[]"} | {"–": "-", "—": "-"}
)
_ELLIPSIS = re.compile(r"\.\.\.|…")
_WHITESPACE = re.compile(r"\s+")
_PARENTHESIZED = re.compile(r"\([^()]*\)")
_TURKISH_FOLD = str.maketrans("çğıöşüâîû", "cgiosuaiu")
_GERMAN_FOLD = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}


class Language(StrEnum):
    GERMAN = "de"
    TURKISH = "tr"


def match_answer(answer: str, expected: str, language: Language) -> EvaluationMethod | None:
    """EXACT or NORMALIZED if the answer is accepted deterministically, otherwise None."""
    if answer.strip() == expected.strip():
        return EvaluationMethod.EXACT
    normalized = normalize(answer, language)
    if normalized and normalized in {normalize(v, language) for v in expected_variants(expected)}:
        return EvaluationMethod.NORMALIZED
    return None


def normalize(text: str, language: Language) -> str:
    """Ignore case, whitespace, punctuation and keyboard-related spelling variants.

    Turkish: "ı/İ" are lower-cased the Turkish way and ç/ğ/ı/ö/ş/ü may be typed without
    diacritics. German: "ae"/"oe"/"ue"/"ss" are accepted for ä/ö/ü/ß (umlauts themselves
    stay significant: "schon" ≠ "schön").
    """
    text = unicodedata.normalize("NFKC", text)
    text = _ELLIPSIS.sub(" ", text).translate(_PUNCTUATION)
    if language is Language.TURKISH:
        text = text.replace("I", "ı").replace("İ", "i").lower().translate(_TURKISH_FOLD)
    else:
        text = text.casefold()
        for umlaut, spelled in _GERMAN_FOLD.items():
            text = text.replace(umlaut, spelled)
    return _WHITESPACE.sub(" ", text).strip()


def expected_variants(expected: str) -> set[str]:
    """Every form of ``expected`` that counts as correct.

    - "Mich nervt es/Ich mag es nicht": whole-phrase alternatives (only when every part
      has several words, so "Trafikte kalmak/beklemek" does not accept "beklemek" alone);
    - "Trafikte kalmak/beklemek": word alternatives → "Trafikte kalmak", "Trafikte beklemek";
    - "an (ein tolles Konzert) denken": with and without the parenthesized part.
    """
    phrases = {expected}
    parts = [part.strip() for part in expected.split("/")]
    if len(parts) > 1 and all(len(part.split()) > 1 for part in parts):
        phrases.update(parts)

    variants: set[str] = set()
    for phrase in phrases:
        # Drop optional parts before splitting words: "(Ergebnisse/Projekte) präsentieren".
        for base in {phrase, _PARENTHESIZED.sub(" ", phrase)}:
            for word_variant in _word_alternatives(base):
                variants.add(word_variant)
                variants.add(_PARENTHESIZED.sub(" ", word_variant))
    return variants


def _word_alternatives(phrase: str) -> list[str]:
    options = [word.split("/") if "/" in word else [word] for word in phrase.split()]
    combinations = itertools.islice(itertools.product(*options), MAX_VARIANTS)
    return [" ".join(words) for words in combinations]
