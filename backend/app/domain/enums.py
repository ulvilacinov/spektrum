from enum import StrEnum


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


class VocabularyItemType(StrEnum):
    WORD = "word"
    NOUN = "noun"
    VERB = "verb"
    PHRASE = "phrase"
    EXPRESSION = "expression"
    GRAMMAR_PATTERN = "grammar_pattern"


# Defined now so the domain vocabulary is in one place; used from the learning steps onward.
class VocabularyStatus(StrEnum):
    NEW = "new"
    LEARNING = "learning"
    WEAK = "weak"
    MASTERED = "mastered"


class QuestionType(StrEnum):
    GERMAN_TO_TURKISH = "german_to_turkish"
    TURKISH_TO_GERMAN = "turkish_to_german"
    FILL_BLANK = "fill_blank"
    SENTENCE_TRANSLATION = "sentence_translation"
    VERB_CONJUGATION = "verb_conjugation"
    ARTICLE = "article"
    PREPOSITION = "preposition"
    FREE_SENTENCE = "free_sentence"
