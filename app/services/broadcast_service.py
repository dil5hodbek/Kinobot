"""Reklama / ommaviy xabar (broadcast) xizmati.

Broadcast asosiy handlerni bloklamasligi uchun ALOHIDA fon vazifasi (asyncio
task) sifatida ishlaydi, o'z DB sessiyasini oladi va bloklangan foydalanuvchilarni
partiyalab (batch) commit qiladi.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.user_repository import UserRepository
from app.utils.i18n import t

logger = logging.getLogger(__name__)

# Telegram limiti ~30 msg/sec; xavfsizlik uchun 25.
_MESSAGES_PER_SECOND = 25
_DELAY = 1 / _MESSAGES_PER_SECOND
_BLOCK_FLUSH_EVERY = 100

# Ishlab turgan fon vazifalarini kuzatib boramiz (GC va graceful shutdown uchun).
_active_jobs: set[asyncio.Task] = set()


@dataclass(slots=True)
class BroadcastResult:
    sent: int = 0
    blocked: int = 0
    failed: int = 0


class BroadcastService:
    """Faqat qabul qiluvchilar sonini hisoblash uchun (request sessiyasida)."""

    def __init__(self, session: AsyncSession) -> None:
        self._user_repo = UserRepository(session)

    async def count_recipients(self) -> int:
        return len(await self._user_repo.get_active_telegram_ids())


async def _copy_once(bot: Bot, chat_id: int, from_chat_id: int, message_id: int) -> None:
    await bot.copy_message(
        chat_id=chat_id, from_chat_id=from_chat_id, message_id=message_id
    )


async def _run_broadcast(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
    from_chat_id: int,
    message_id: int,
    admin_id: int,
    lang: str,
) -> None:
    """Fon vazifasi: barcha faol foydalanuvchilarga reklamani yuboradi."""
    # 1) Qabul qiluvchilarni bir marta o'qib olamiz (qisqa sessiya).
    async with session_factory() as session:
        recipients = await UserRepository(session).get_active_telegram_ids()

    result = BroadcastResult()
    blocked_ids: list[int] = []

    async def flush_blocked() -> None:
        if not blocked_ids:
            return
        async with session_factory() as session:
            await UserRepository(session).set_blocked_bulk(list(blocked_ids))
            await session.commit()
        blocked_ids.clear()

    try:
        for telegram_id in recipients:
            try:
                await _copy_once(bot, telegram_id, from_chat_id, message_id)
                result.sent += 1
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after)
                try:
                    await _copy_once(bot, telegram_id, from_chat_id, message_id)
                    result.sent += 1
                except TelegramAPIError:
                    result.failed += 1
            except TelegramForbiddenError:
                result.blocked += 1
                blocked_ids.append(telegram_id)
            except TelegramAPIError as exc:
                logger.warning("Broadcast xatosi (%s): %s", telegram_id, exc)
                result.failed += 1

            if len(blocked_ids) >= _BLOCK_FLUSH_EVERY:
                await flush_blocked()

            await asyncio.sleep(_DELAY)
    finally:
        # shutdown_jobs() bot to'xtaganда task.cancel() qiladi — CancelledError
        # shu yerda ushlanadi (finally har doim ishlaydi). Flush BAJARILISHI
        # SHART, aks holda oxirgi <_BLOCK_FLUSH_EVERY tagacha "bloklagan"
        # foydalanuvchi is_blocked=True bo'lib yozilmay qoladi — ular
        # keyingi broadcast'da yana (behuda) qayta urinilardi.
        await flush_blocked()

    # Yakuniy hisobot adminga
    try:
        await bot.send_message(
            admin_id,
            t(
                "broadcast_done",
                lang,
                sent=result.sent,
                blocked=result.blocked,
                failed=result.failed,
            ),
        )
    except TelegramAPIError:
        logger.info(
            "Broadcast yakunlandi: sent=%s blocked=%s failed=%s",
            result.sent,
            result.blocked,
            result.failed,
        )


def start_broadcast_job(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    from_chat_id: int,
    message_id: int,
    admin_id: int,
    lang: str,
) -> None:
    """Broadcastni fon vazifasi sifatida ishga tushiradi (bloklamaydi)."""
    task = asyncio.create_task(
        _run_broadcast(
            bot,
            session_factory,
            from_chat_id=from_chat_id,
            message_id=message_id,
            admin_id=admin_id,
            lang=lang,
        )
    )
    _active_jobs.add(task)
    task.add_done_callback(_active_jobs.discard)


async def shutdown_jobs() -> None:
    """Ishlab turgan broadcast vazifalarini bekor qiladi (graceful shutdown)."""
    for task in list(_active_jobs):
        task.cancel()
    if _active_jobs:
        await asyncio.gather(*_active_jobs, return_exceptions=True)
