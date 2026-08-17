"""link kinolar (source_type/external_url) + genre indeksi

Revision ID: 0003_link_movies
Revises: 0002_lower_trgm
Create Date: 2024-01-03 00:00:00.000000

Ikki mustaqil o'zgarish bitta migratsiyada:
  1. Link orqali kino qo'shish: `source_type` ('channel'|'link'),
     `external_url`. channel_id/message_id endi ixtiyoriy (faqat
     source_type='channel' uchun majburiy). CHECK constraint baza
     darajasida noto'g'ri kombinatsiyani rad etadi.
  2. `genre` ustuniga oddiy btree indeks — janr bo'yicha guruhlash
     (ko'p auditoriya bilan sekinlashmasin).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003_link_movies"
down_revision: Union[str, None] = "0002_lower_trgm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Mavjud qatorlar "channel" hisoblanadi (server_default) — backfill shart emas.
    op.execute(
        "ALTER TABLE movies ADD COLUMN source_type VARCHAR(10) "
        "NOT NULL DEFAULT 'channel'"
    )
    op.execute("ALTER TABLE movies ADD COLUMN external_url VARCHAR(500)")

    # Link kino uchun channel_id/message_id ma'nosiz — ixtiyoriy qilamiz.
    op.execute("ALTER TABLE movies ALTER COLUMN channel_id DROP NOT NULL")
    op.execute("ALTER TABLE movies ALTER COLUMN message_id DROP NOT NULL")

    # Baza darajasida qat'iy tekshiruv: channel kino -> channel_id+message_id
    # SHART; link kino -> external_url SHART. Ilova xatosi bilan ham
    # noto'g'ri yozuv bazaga tushmaydi.
    op.execute(
        "ALTER TABLE movies ADD CONSTRAINT ck_movies_source_fields CHECK ("
        "  (source_type = 'channel' AND channel_id IS NOT NULL "
        "     AND message_id IS NOT NULL AND external_url IS NULL)"
        "  OR (source_type = 'link' AND external_url IS NOT NULL)"
        ")"
    )

    op.execute("CREATE INDEX ix_movies_genre ON movies (genre)")


def downgrade() -> None:
    # DIQQAT: agar downgrade paytida source_type='link' qatorlar mavjud
    # bo'lsa (channel_id NULL), quyidagi SET NOT NULL xato beradi — bu
    # kutilgan: eski sxema link kinolarni ifodalay olmaydi, avval o'sha
    # qatorlarni qo'lda hal qilish (o'chirish yoki channel_id to'ldirish) kerak.
    op.execute("DROP INDEX IF EXISTS ix_movies_genre")
    op.execute("ALTER TABLE movies DROP CONSTRAINT IF EXISTS ck_movies_source_fields")
    op.execute("ALTER TABLE movies ALTER COLUMN channel_id SET NOT NULL")
    op.execute("ALTER TABLE movies ALTER COLUMN message_id SET NOT NULL")
    op.execute("ALTER TABLE movies DROP COLUMN external_url")
    op.execute("ALTER TABLE movies DROP COLUMN source_type")
