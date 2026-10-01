"""user ai settings

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-29 18:05:00.000000+00:00

Each user's AI provider, model and encrypted API key (settings page).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_ai_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "provider",
            sa.Enum(
                "gemini",
                "openai",
                "anthropic",
                "openai_compatible",
                name="aiproviderkind",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("api_key_hint", sa.String(length=8), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_ai_settings_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_ai_settings")),
        sa.UniqueConstraint("user_id", name=op.f("uq_user_ai_settings_user_id")),
    )


def downgrade() -> None:
    op.drop_table("user_ai_settings")
