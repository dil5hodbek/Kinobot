"""Durable (DB-backed) broadcast tizimi.

AVVALGI dizayn: broadcast = jarayon xotirasidagi asyncio.Task + RAMdagi
to'liq qabul qiluvchilar ro'yxati. Bot restart bo'lsa broadcast izsiz
yo'qolardi; millionlab foydalanuvchida ro'yxat RAMni yeb qo'yardi; bir
nechta bot instansida esa umuman nazoratsiz edi.

YANGI dizayn (at-least-once semantika):

    Admin tasdiqlaydi
        ↓
    broadcast_jobs jadvaliga yozuv (status=pending)
        ↓
    Worker (har instansda bitta, FOR UPDATE SKIP LOCKED bilan claim)
        ↓
    Qabul qiluvchilar keyset-batch bilan o'qiladi (RAMga to'liq YUKLANMAYDI)
        ↓
    Har batchdan keyin progress (sent/blocked/failed + kursor) DB'ga yoziladi
        ↓
    Tugagach admin xabardor qilinadi

Restart: 'running' jobning heartbeat'i eskirsa (2 daqiqa) keyingi worker
uni qayta claim qiladi va `last_processed_user_id` kursoridan davom etadi.
Eng yomon holatda oxirgi to'liq saqlanmagan batch (<=_BATCH_SIZE xabar)
qayta yuborilishi mumkin — bu hujjatlashtirilgan (exactly-once Telegram
bilan texnik jihatdan imkonsiz).

Telegram tezlik chegarasi: ketma-ket yuborish + har xabar orasida pacing
(~25 msg/s) + RetryAfter'ga so'zsiz bo'ysunish. Bir instans = bitta worker,
shuning uchun global bosim ham chegaralangan bo'ladi.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.broadcast_job_repository import BroadcastJobRepository
from app.repositories.user_repository import UserRepository
from app.utils.i18n import t

logger = logging.getLogger(__name__)

# Telegram limiti ~30 msg/sec; xavfsizlik uchun 25.
_MESSAGES_PER_SECOND = 25
_DELAY = 1 / _MESSAGES_PER_SECOND
# Har batchda nechta qabul qiluvchi o'qiladi va progress qanchada saqlanadi.
_BATCH_SIZE = 500
# Yangi job yo'qligida worker qancha uxlaydi.
_IDLE_POLL_SEC = 3.0

# Ishlab turgan worker tasklari (graceful shutdown uchun — endi bu YAKKA
# haqiqat manbai EMAS, shunchaki jarayonni toza to'xtatish vositasi).
_active_jobs: set[asyncio.Task] = set()


@dataclass(slots=True)
class SendOutcome:
    sent: int = 0
    blocked: int = 0
    failed: int = 0


class BroadcastService:
    """Request sessiyasida: job yaratish/bekor qilish/hisoblash."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session)
        self._job_repo = BroadcastJobRepository(session)

    async def count_recipients(self) -> int:
        return await self._user_repo.count_active_recipients()

    async def create_job(
        self, *, created_by: int, from_chat_id: int, message_id: int, lang: str
    ) -> int:
        total = await self._user_repo.count_active_recipients()
        job = await self._job_repo.create(
            created_by=created_by,
            from_chat_id=from_chat_id,
            message_id=message_id,
            lang=lang,
            total_recipients=total,
        )
        return job.id

    async def cancel_job(self, job_id: int) -> bool:
        return await self._job_repo.request_cancel(job_id)


async def _send_one(
    bot: Bot, chat_id: int, from_chat_id: int, message_id: int
) -> str:
    """Bitta qabul qiluvchiga yuboradi. Natija: 'sent'|'blocked'|'failed'."""
    for attempt in (1, 2):
        try:
            await bot.copy_message(
                chat_id=chat_id, from_chat_id=from_chat_id, message_id=message_id
            )
            return "sent"
        except TelegramRetryAfter as exc:
            # Telegram aniq kutish vaqtini aytdi — so'zsiz bo'ysunamiz.
            await asyncio.sleep(exc.retry_after)
            if attempt == 2:
                return "failed"
        except TelegramForbiddenError:
            return "blocked"
        except TelegramBadRequest as exc:
            if "chat not found" in str(exc).lower():
                # Foydalanuvchi hisobini o'chirgan — keyingi broadcastlarda
                # behuda urinmaslik uchun bloklangan deb belgilanadi.
                return "blocked"
            logger.warning("Broadcast xatosi (%s): %s", chat_id, exc)
            return "failed"
        except TelegramNetworkError as exc:
            if attempt == 1:
                await asyncio.sleep(1)
            else:
                logger.warning("Broadcast tarmoq xatosi (%s): %s", chat_id, exc)
                return "failed"
        except TelegramAPIError as exc:
            logger.warning("Broadcast xatosi (%s): %s", chat_id, exc)
            return "failed"
    return "failed"


async def _process_job(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
    job_id: int,
    *,
    from_chat_id: int,
    message_id: int,
    admin_id: int,
    lang: str,
    sent: int,
    blocked: int,
    failed: int,
    cursor: int,
) -> None:
    """Bitta jobni (kerak bo'lsa kursordan davom etib) oxirigacha yuboradi."""
    outcome = SendOutcome(sent=sent, blocked=blocked, failed=failed)
    cancelled = False

    while True:
        # Har batch oldidan: admin bekor qilmaganmi + qabul qiluvchilar.
        async with session_factory() as session:
            status = await BroadcastJobRepository(session).current_status(job_id)
            if status == "cancelled":
                cancelled = True
                break
            batch = await UserRepository(session).get_active_recipients_batch(
                cursor, _BATCH_SIZE
            )

        if not batch:
            break

        blocked_tg_ids: list[int] = []
        for user_id, telegram_id in batch:
            result = await _send_one(bot, telegram_id, from_chat_id, message_id)
            if result == "sent":
                outcome.sent += 1
            elif result == "blocked":
                outcome.blocked += 1
                blocked_tg_ids.append(telegram_id)
            else:
                outcome.failed += 1
            cursor = user_id
            await asyncio.sleep(_DELAY)

        # Batch tugadi — progress + bloklanganlar QISQA tranzaksiyada.
        async with session_factory() as session:
            if blocked_tg_ids:
                await UserRepository(session).set_blocked_bulk(blocked_tg_ids)
            await BroadcastJobRepository(session).save_progress(
                job_id,
                sent=outcome.sent,
                blocked=outcome.blocked,
                failed=outcome.failed,
                cursor=cursor,
            )
            await session.commit()

    final_status = "cancelled" if cancelled else "completed"
    async with session_factory() as session:
        repo = BroadcastJobRepository(session)
        await repo.save_progress(
            job_id,
            sent=outcome.sent,
            blocked=outcome.blocked,
            failed=outcome.failed,
            cursor=cursor,
        )
        if not cancelled:
            await repo.finish(job_id, final_status)
        await session.commit()

    # Yakuniy hisobot adminga (best-effort)
    try:
        await bot.send_message(
            admin_id,
            t(
                "broadcast_done",
                lang,
                sent=outcome.sent,
                blocked=outcome.blocked,
                failed=outcome.failed,
            ),
        )
    except TelegramAPIError:
        pass
    logger.info(
        "Broadcast #%s %s: sent=%s blocked=%s failed=%s",
        job_id,
        final_status,
        outcome.sent,
        outcome.blocked,
        outcome.failed,
    )


async def broadcast_worker_loop(
    bot: Bot, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Cheksiz worker: pending (yoki o'lib qolgan running) joblarni oladi."""
    logger.info("Broadcast worker ishga tushdi.")
    while True:
        try:
            async with session_factory() as session:
                job = await BroadcastJobRepository(session).claim_next()
                if job is not None:
                    # Claim tranzaksiyasini yopamiz (SKIP LOCKED qulfi
                    # bo'shaydi — status='running' endi boshqa workerlarni
                    # to'sadi, heartbeat esa o'lganlarni qutqaradi).
                    params = dict(
                        job_id=job.id,
                        from_chat_id=job.from_chat_id,
                        message_id=job.message_id,
                        admin_id=job.created_by,
                        lang=job.lang,
                        sent=job.sent_count,
                        blocked=job.blocked_count,
                        failed=job.failed_count,
                        cursor=job.last_processed_user_id,
                    )
                    await session.commit()
                else:
                    params = None

            if params is None:
                await asyncio.sleep(_IDLE_POLL_SEC)
                continue

            logger.info(
                "Broadcast #%s boshlandi (kursor=%s).",
                params["job_id"],
                params["cursor"],
            )
            await _process_job(bot, session_factory, **params)

        except asyncio.CancelledError:
            # Graceful shutdown: job DB'da 'running' qoladi, heartbeat
            # eskirgach keyingi ishga tushishda davom ettiriladi.
            logger.info("Broadcast worker to'xtatildi (joblar DB'da saqlanadi).")
            raise
        except Exception:  # noqa: BLE001 - worker hech qachon o'lmasligi kerak
            logger.exception("Broadcast worker xatosi — 5s dan keyin davom etadi.")
            await asyncio.sleep(5)


def start_broadcast_worker(
    bot: Bot, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Worker taskini ishga tushiradi (main.py'dan bir marta chaqiriladi)."""
    task = asyncio.create_task(broadcast_worker_loop(bot, session_factory))
    _active_jobs.add(task)
    task.add_done_callback(_active_jobs.discard)


async def shutdown_jobs() -> None:
    """Worker tasklarini bekor qiladi (graceful shutdown).

    Joblarning o'zi DB'da — hech narsa yo'qolmaydi."""
    for task in list(_active_jobs):
        task.cancel()
    if _active_jobs:
        await asyncio.gather(*_active_jobs, return_exceptions=True)
