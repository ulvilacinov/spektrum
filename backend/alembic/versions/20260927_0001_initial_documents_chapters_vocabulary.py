"""initial documents, chapters, vocabulary items

Revision ID: 0001
Revises:
Create Date: 2026-09-27

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOCUMENT_STATUSES = ("uploaded", "parsing", "parsed", "failed")
VOCABULARY_ITEM_TYPES = ("word", "noun", "verb", "phrase", "expression", "grammar_pattern")


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("original_file_name", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*DOCUMENT_STATUSES, name="documentstatus", native_enum=False, length=20),
            server_default="uploaded",
            nullable=False,
        ),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index(op.f("ix_documents_user_id"), "documents", ["user_id"])
    op.create_index(op.f("ix_documents_status"), "documents", ["status"])

    op.create_table(
        "chapters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("source_start_page", sa.Integer(), nullable=False),
        sa.Column("source_end_page", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "source_start_page >= 1", name=op.f("ck_chapters_start_page_positive")
        ),
        sa.CheckConstraint(
            "source_end_page >= source_start_page", name=op.f("ck_chapters_page_range_valid")
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_chapters_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chapters")),
        sa.UniqueConstraint("document_id", "order", name=op.f("uq_chapters_document_id_order")),
    )
    op.create_index(op.f("ix_chapters_document_id"), "chapters", ["document_id"])

    op.create_table(
        "vocabulary_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("german", sa.String(length=500), nullable=False),
        sa.Column("turkish", sa.String(length=500), nullable=False),
        sa.Column(
            "item_type",
            sa.Enum(
                *VOCABULARY_ITEM_TYPES, name="vocabularyitemtype", native_enum=False, length=32
            ),
            nullable=False,
        ),
        sa.Column("article", sa.String(length=20), nullable=True),
        sa.Column("base_verb", sa.String(length=255), nullable=True),
        sa.Column("prateritum", sa.String(length=255), nullable=True),
        sa.Column("perfekt", sa.String(length=255), nullable=True),
        sa.Column("preposition", sa.String(length=50), nullable=True),
        sa.Column("grammatical_case", sa.String(length=50), nullable=True),
        sa.Column("example_german", sa.Text(), nullable=True),
        sa.Column("example_turkish", sa.Text(), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            name=op.f("fk_vocabulary_items_chapter_id_chapters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vocabulary_items")),
        sa.UniqueConstraint(
            "chapter_id", "order", name=op.f("uq_vocabulary_items_chapter_id_order")
        ),
    )
    op.create_index(op.f("ix_vocabulary_items_chapter_id"), "vocabulary_items", ["chapter_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_vocabulary_items_chapter_id"), table_name="vocabulary_items")
    op.drop_table("vocabulary_items")
    op.drop_index(op.f("ix_chapters_document_id"), table_name="chapters")
    op.drop_table("chapters")
    op.drop_index(op.f("ix_documents_status"), table_name="documents")
    op.drop_index(op.f("ix_documents_user_id"), table_name="documents")
    op.drop_table("documents")
