"""100K+ auditoriya uchun: indekslar, durable broadcast, admin audit log

Revision ID: 0005_scale_hardening
Revises: 0004_curated_trending
Create Date: 2024-01-05 00:00:00.000000

Uch mustaqil o'zgarish:
  1. Indekslar (so'rov rejalariga asoslangan):
     - users: broadcast qabul qiluvchilar uchun partial index
       (WHERE is_blocked = false — faqat faol foydalanuvchilar skanlanadi,
       keyset pagination `id > cursor ORDER BY id` shu indeks bilan ishlaydi).
     - users.last_active_at: statistika (`count_active_since`) seq-scan
       bo'lmasligi uchun.
     - movie_views(user_id, viewed_at): kelajakdagi foydalanuvchi tarixi
       so'rovlari uchun (0001'da faqat movie_id tomoni indekslangan edi).
  2. broadcast_jobs — durable (DB-backed) broadcast:
     jarayon xotirasidagi asyncio.Task YAKKA haqiqat manbai bo'lmasligi uchun.
     Bot restart bo'lsa job yo'qolmaydi, `last_processed_user_id` kursoridan
     davom etadi. `status` + `heartbeat_at` bilan bir nechta instans xavfsiz
     ishlaydi (eskirgan 'running' joblar qayta claim qilinadi).
  3. admin_audit_logs — "kim nimani qachon qildi" (kino qo'shish/o'chirish/
     tahrirlash, trend, kanal, broadcast).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005_scale_hardening"
down_revision: Union[str, None] = "0004_curated_trending"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === 1. Indekslar ===
    op.execute(
        "CREATE INDEX ix_users_broadcast_recipients "
        "ON users (id, telegram_id) WHERE is_blocked = false"
    )
    op.execute("CREATE INDEX ix_users_last_active_at ON users (last_active_at)")
    op.execute(
        "CREATE INDEX ix_movie_views_user_viewed "
        "ON movie_views (user_id, viewed_at)"
    )

    # === 2. Durable broadcast joblar ===
    op.execute(
        """
        CREATE TABLE broadcast_jobs (
            id BIGSERIAL PRIMARY KEY,
            status VARCHAR(10) NOT NULL DEFAULT 'pending',
            created_by BIGINT NOT NULL,
            from_chat_id BIGINT NOT NULL,
            message_id BIGINT NOT NULL,
            lang VARCHAR(5) NOT NULL DEFAULT 'uz',
            total_recipients BIGINT NOT NULL DEFAULT 0,
            sent_count BIGINT NOT NULL DEFAULT 0,
            blocked_count BIGINT NOT NULL DEFAULT 0,
            failed_count BIGINT NOT NULL DEFAULT 0,
            last_processed_user_id BIGINT NOT NULL DEFAULT 0,
            error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            started_at TIMESTAMPTZ,
            heartbeat_at TIMESTAMPTZ,
            finished_at TIMESTAMPTZ,
            CONSTRAINT ck_broadcast_jobs_status CHECK (
                status IN ('pending','running','completed','failed','cancelled')
            )
        )
        """
    )
    # Worker "keyingi job" qidiruvi uchun (pending yoki o'lib qolgan running)
    op.execute(
        "CREATE INDEX ix_broadcast_jobs_claim "
        "ON broadcast_jobs (status, id) "
        "WHERE status IN ('pending','running')"
    )

    # === 3. Admin audit log ===
    op.execute(
        """
        CREATE TABLE admin_audit_logs (
            id BIGSERIAL PRIMARY KEY,
            admin_id BIGINT NOT NULL,
            action VARCHAR(40) NOT NULL,
            entity_type VARCHAR(20) NOT NULL,
            entity_id VARCHAR(64),
            metadata TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_admin_audit_logs_created ON admin_audit_logs (created_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS admin_audit_logs")
    op.execute("DROP TABLE IF EXISTS broadcast_jobs")
    op.execute("DROP INDEX IF EXISTS ix_movie_views_user_viewed")
    op.execute("DROP INDEX IF EXISTS ix_users_last_active_at")
    op.execute("DROP INDEX IF EXISTS ix_users_broadcast_recipients")
