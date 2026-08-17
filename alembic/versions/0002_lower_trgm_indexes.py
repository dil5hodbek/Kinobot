"""trigram indekslarni lower(title) ifodasiga o'tkazish (case-insensitive qidiruv)

Revision ID: 0002_lower_trgm
Revises: 0001_initial
Create Date: 2024-01-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002_lower_trgm"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Eski (case-sensitive) trigram indekslarni olib tashlaymiz
    op.execute("DROP INDEX IF EXISTS ix_movies_title_uz_trgm")
    op.execute("DROP INDEX IF EXISTS ix_movies_title_ru_trgm")
    op.execute("DROP INDEX IF EXISTS ix_movies_title_en_trgm")

    # lower(...) ifodasiga indeks — case-insensitive qidiruv indeksdan foydalanadi
    op.execute(
        "CREATE INDEX ix_movies_title_uz_trgm ON movies "
        "USING gin (lower(title_uz) gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_movies_title_ru_trgm ON movies "
        "USING gin (lower(coalesce(title_ru, '')) gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_movies_title_en_trgm ON movies "
        "USING gin (lower(coalesce(title_en, '')) gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_movies_title_uz_trgm")
    op.execute("DROP INDEX IF EXISTS ix_movies_title_ru_trgm")
    op.execute("DROP INDEX IF EXISTS ix_movies_title_en_trgm")
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
