"""Durable broadcast joblar bilan ishlovchi repository.

Multi-instance xavfsizligi:
  • `claim_next()` — `FOR UPDATE SKIP LOCKED` bilan: ikki worker bir jobni
    hech qachon bir vaqtda ololmaydi.
  • O'lib qolgan instansning 'running' jobi `heartbeat_at` eskirganda
    (STALE_RUNNING_AFTER) qayta claim qilinadi — restartdan keyin broadcast
    yo'qolmaydi, kursordan davom etadi.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broadcast_job import BroadcastJob

# Shu vaqtdan beri heartbeat bo'lmagan 'running' job — egasi o'lgan deb hisoblanadi.
STALE_RUNNING_AFTER = timedelta(minutes=2)


class BroadcastJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        created_by: int,
        from_chat_id: int,
        message_id: int,
        lang: str,
        total_recipients: int,
    ) -> BroadcastJob:
        job = BroadcastJob(
            created_by=created_by,
            from_chat_id=from_chat_id,
            message_id=message_id,
            lang=lang,
            total_recipients=total_recipients,
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(self, job_id: int) -> BroadcastJob | None:
        result = await self._session.execute(
            select(BroadcastJob).where(BroadcastJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def claim_next(self) -> BroadcastJob | None:
        """Keyingi bajarilishi kerak jobni atomik oladi (yoki None).

        'pending' YOKI heartbeat'i eskirgan 'running' (o'lgan instansniki).
        SKIP LOCKED — parallel workerlar bir-birini kutmaydi ham,
        to'qnashmaydi ham.
        """
        stale_before = datetime.now(timezone.utc) - STALE_RUNNING_AFTER
        result = await self._session.execute(
            select(BroadcastJob)
            .where(
                (BroadcastJob.status == "pending")
                | (
                    (BroadcastJob.status == "running")
                    & (BroadcastJob.heartbeat_at < stale_before)
                )
            )
            .order_by(BroadcastJob.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = result.scalar_one_or_none()
        if job is None:
            return None

        now = datetime.now(timezone.utc)
        job.status = "running"
        job.heartbeat_at = now
        if job.started_at is None:
            job.started_at = now
        await self._session.flush()
        return job

    async def save_progress(
        self,
        job_id: int,
        *,
        sent: int,
        blocked: int,
        failed: int,
        cursor: int,
    ) -> None:
        """Batch tugagach progressni yozadi + heartbeat yangilaydi."""
        await self._session.execute(
            update(BroadcastJob)
            .where(BroadcastJob.id == job_id)
            .values(
                sent_count=sent,
                blocked_count=blocked,
                failed_count=failed,
                last_processed_user_id=cursor,
                heartbeat_at=func.now(),
            )
        )

    async def finish(
        self, job_id: int, status: str, error: str | None = None
    ) -> None:
        await self._session.execute(
            update(BroadcastJob)
            .where(BroadcastJob.id == job_id)
            .values(status=status, error=error, finished_at=func.now())
        )

    async def request_cancel(self, job_id: int) -> bool:
        """Adminning bekor qilish so'rovi. Faqat tugallanmagan joblar uchun."""
        result = await self._session.execute(
            update(BroadcastJob)
            .where(
                BroadcastJob.id == job_id,
                BroadcastJob.status.in_(("pending", "running")),
            )
            .values(status="cancelled", finished_at=func.now())
        )
        return result.rowcount > 0

    async def current_status(self, job_id: int) -> str | None:
        """Worker har batchda tekshiradi (admin bekor qilgan bo'lishi mumkin)."""
        result = await self._session.execute(
            select(BroadcastJob.status).where(BroadcastJob.id == job_id)
        )
        return result.scalar_one_or_none()
