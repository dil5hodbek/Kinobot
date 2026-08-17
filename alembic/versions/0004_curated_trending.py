"""qo'lda boshqariladigan trend kinolar (is_trending)

Revision ID: 0004_curated_trending
Revises: 0003_link_movies
Create Date: 2024-01-04 00:00:00.000000

Avval "trend" ko'rishlar soni (views_count) bo'yicha AVTOMATIK hisoblanardi.
Endi admin panelda qo'lda boshqariladi: `is_trending` — shu kino trend
ro'yxatidami, `trending_added_at` — trendga qo'shilgan vaqt (ro'yxatda eng
yangi qo'shilgani birinchi ko'rsatiladi). Faqat `is_trending=true` bo'lgan
qatorlar uchun qidiriladigan bo'lgani sabab — partial index.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004_curated_trending"
down_revision: Union[str, None] = "0003_link_movies"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE movies ADD COLUMN is_trending BOOLEAN NOT NULL DEFAULT false"
    )
    op.execute("ALTER TABLE movies ADD COLUMN trending_added_at TIMESTAMPTZ")
    op.execute(
        "CREATE INDEX ix_movies_is_trending ON movies (trending_added_at DESC) "
        "WHERE is_trending IS TRUE"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_movies_is_trending")
    op.execute("ALTER TABLE movies DROP COLUMN trending_added_at")
    op.execute("ALTER TABLE movies DROP COLUMN is_trending")
