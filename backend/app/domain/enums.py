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


class ErrorType(StrEnum):
    ARTICLE = "article"
    CASE = "case"
    PREPOSITION = "preposition"
    WORD_ORDER = "word_order"
    VERB_CONJUGATION = "verb_conjugation"
    SPELLING = "spelling"
    VOCABULARY_USAGE = "vocabulary_usage"
    MEANING = "meaning"
    GRAMMAR = "grammar"


class EvaluationMethod(StrEnum):
    EXACT = "exact"  # identical to an expected answer
    NORMALIZED = "normalized"  # equal after deterministic normalization
    RULE = "rule"  # closed question (article, preposition, …) judged without AI
    AI = "ai"


class SessionMode(StrEnum):
    NEW = "new"  # the chapter's next unstudied words
    REVIEW = "review"  # studied but not yet mastered words, weak ones first


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class AIProviderKind(StrEnum):
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    # Any service with OpenAI's Chat Completions API (DeepSeek, OpenRouter, Groq, ...).
    OPENAI_COMPATIBLE = "openai_compatible"
