"""initial schema (users, movies, movie_views, required_channels) + pg_trgm

Revision ID: 0001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pg_trgm fuzzy qidiruv uchun
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # === users ===
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=5), nullable=False, server_default="uz"),
        sa.Column(
            "is_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])

    # === movies ===
    op.create_table(
        "movies",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("title_uz", sa.String(length=255), nullable=False),
        sa.Column("title_ru", sa.String(length=255), nullable=True),
        sa.Column("title_en", sa.String(length=255), nullable=True),
        sa.Column("year", sa.SmallInteger(), nullable=True),
        sa.Column("genre", sa.String(length=100), nullable=True),
        sa.Column(
            "views_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_movies_code", "movies", ["code"])
    op.execute(
        "CREATE INDEX ix_movies_views ON movies (views_count DESC) WHERE is_active"
    )
    op.execute(
        "CREATE INDEX ix_movies_title_uz_trgm ON movies "
        "USING gin (title_uz gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_movies_title_ru_trgm ON movies "
        "USING gin (title_ru gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_movies_title_en_trgm ON movies "
        "USING gin (title_en gin_trgm_ops)"
    )

    # === movie_views ===
    op.create_table(
        "movie_views",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("movie_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "viewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_movie_views_movie_viewed", "movie_views", ["movie_id", "viewed_at"]
    )

    # === required_channels ===
    op.create_table(
        "required_channels",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("channel_username", sa.String(length=64), nullable=False),
        sa.Column("channel_title", sa.String(length=255), nullable=True),
        sa.Column("invite_link", sa.String(length=255), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_username"),
    )


def downgrade() -> None:
    op.drop_table("required_channels")
    op.drop_index("ix_movie_views_movie_viewed", table_name="movie_views")
    op.drop_table("movie_views")
    op.execute("DROP INDEX IF EXISTS ix_movies_title_en_trgm")
    op.execute("DROP INDEX IF EXISTS ix_movies_title_ru_trgm")
    op.execute("DROP INDEX IF EXISTS ix_movies_title_uz_trgm")
    op.execute("DROP INDEX IF EXISTS ix_movies_views")
    op.drop_index("ix_movies_code", table_name="movies")
    op.drop_table("movies")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
