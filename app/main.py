"""Bot kirish nuqtasi: dispatcher, middleware'lar, polling."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.config import settings
from app.database import session_factory
from app.handlers import build_router
from app.middlewares.db_session import DbSessionMiddleware
from app.middlewares.rate_limit import RateLimitMiddleware
from app.middlewares.subscription import SubscriptionMiddleware
from app.middlewares.user_context import UserContextMiddleware
from app.utils.i18n import load_translations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("kinobot")


async def _make_storage(redis: Redis) -> BaseStorage:
    """Redis mavjud bo'lsa RedisStorage, aks holda MemoryStorage (zaxira)."""
    try:
        await redis.ping()
        logger.info("FSM uchun RedisStorage ishlatilmoqda.")
        return RedisStorage(redis)
    except Exception as exc:  # noqa: BLE001 - Redis ishlamasa ham ishga tushamiz
        logger.warning(
            "Redis mavjud emas (%s) — FSM uchun MemoryStorage ishlatiladi.", exc
        )
        return MemoryStorage()


def _register_middlewares(dp: Dispatcher, redis: Redis) -> None:
    # DB sessiya — butun update'ni o'raydi (eng tashqi).
    dp.update.outer_middleware(DbSessionMiddleware(session_factory))

    # Message va callback uchun kontekst zanjiri (ro'yxat tartibida ishlaydi).
    for observer in (dp.message, dp.callback_query):
        observer.middleware(UserContextMiddleware())
        observer.middleware(RateLimitMiddleware(redis))
        observer.middleware(SubscriptionMiddleware(redis))


async def main() -> None:
    load_translations()

    redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=settings.redis_max_connections,
    )
    storage = await _make_storage(redis)

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties())
    dp = Dispatcher(storage=storage)

    # Handlerlarga qo'shimcha kontekst uzatamiz
    dp["redis"] = redis
    dp["session_factory"] = session_factory

    _register_middlewares(dp, redis)
    dp.include_router(build_router())

    try:
        me = await bot.get_me()
        logger.info("Bot ishga tushdi: @%s (id=%s)", me.username, me.id)
        logger.info(
            "STORAGE_CHANNEL_ID=%s | REQUIRED_CHANNELS=%s | ADMIN_IDS=%s",
            settings.storage_channel_id,
            settings.required_channels,
            settings.admin_ids,
        )
        if settings.storage_channel_id == -1001234567890:
            logger.warning(
                "DIQQAT: STORAGE_CHANNEL_ID hali SOXTA (-1001234567890). "
                "Kanaldan avto qo'shish ISHLAMAYDI. Real kanal ID'sini .env ga yozing."
            )
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        # Fondagi vazifalarni (masalan broadcast) to'xtatamiz
        from app.services.broadcast_service import shutdown_jobs

        await shutdown_jobs()
        await bot.session.close()
        await redis.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
