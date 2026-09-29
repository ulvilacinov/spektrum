"""users and auth sessions

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-29 11:56:19.157048+00:00

Existing data (from the single-user era, user_id 1 or NULL) is given to a user "admin"
with id 1 and no password; set one with ``python -m app.cli set-password admin``.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_USER_ID = 1


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_auth_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_auth_sessions_token_hash")),
    )
    op.create_index(op.f("ix_auth_sessions_user_id"), "auth_sessions", ["user_id"], unique=False)

    # Hand existing data to the legacy user, which only exists if there is data to own.
    op.execute(
        f"""
        INSERT INTO users (id, username, password_hash)
        SELECT {LEGACY_USER_ID}, 'admin', ''
        WHERE EXISTS (SELECT 1 FROM documents)
           OR EXISTS (SELECT 1 FROM learning_sessions)
           OR EXISTS (SELECT 1 FROM user_vocabulary_progress)
        """
    )
    op.execute(f"UPDATE documents SET user_id = {LEGACY_USER_ID} WHERE user_id IS NULL")
    op.execute(
        f"UPDATE learning_sessions SET user_id = {LEGACY_USER_ID} "
        "WHERE user_id NOT IN (SELECT id FROM users)"
    )
    op.execute(
        f"UPDATE user_vocabulary_progress SET user_id = {LEGACY_USER_ID} "
        "WHERE user_id NOT IN (SELECT id FROM users)"
    )
    # The explicit id bypassed the sequence; continue after it.
    op.execute(
        "SELECT setval(pg_get_serial_sequence('users', 'id'), "
        "COALESCE((SELECT MAX(id) FROM users), 0) + 1, false)"
    )

    op.alter_column("documents", "user_id", existing_type=sa.INTEGER(), nullable=False)
    op.create_foreign_key(
        op.f("fk_documents_user_id_users"),
        "documents",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_learning_sessions_user_id_users"),
        "learning_sessions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_user_vocabulary_progress_user_id_users"),
        "user_vocabulary_progress",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_user_vocabulary_progress_user_id_users"),
        "user_vocabulary_progress",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_learning_sessions_user_id_users"), "learning_sessions", type_="foreignkey"
    )
    op.drop_constraint(op.f("fk_documents_user_id_users"), "documents", type_="foreignkey")
    op.alter_column("documents", "user_id", existing_type=sa.INTEGER(), nullable=True)
    op.drop_index(op.f("ix_auth_sessions_user_id"), table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_table("users")
