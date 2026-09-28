# Import every model here so Base.metadata is complete for Alembic and relationships resolve.
from app.db.models.chapter import Chapter
from app.db.models.document import Document
from app.db.models.learning_session import LearningSession, LearningSessionItem
from app.db.models.user_vocabulary_progress import UserVocabularyProgress
from app.db.models.vocabulary_item import VocabularyItem

__all__ = [
    "Chapter",
    "Document",
    "LearningSession",
    "LearningSessionItem",
    "UserVocabularyProgress",
    "VocabularyItem",
]
