"""Bot kirish nuqtasi: dispatcher, middleware'lar, HTTP server, polling/webhook.

Ishga tushirish rejimlari (.env orqali):
  BOT_MODE=polling  (standart) — bitta instans uchun, dev va kichik yuk.
  BOT_MODE=webhook             — bir nechta instans + reverse proxy uchun.

Har ikkala rejimda ham /health/live, /health/ready va /metrics HTTP
endpointlari ishlaydi (app/observability/http_server.py).

BOT_ENV=production bo'lsa Redis MAJBURIY: MemoryStorage'ga jimgina o'tish
taqiqlanadi, chunki u (a) restartda FSM holatini yo'qotadi va (b) bir
nechta instansda holatni butunlay buzadi.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from redis.asyncio import Redis

from app.config import settings
from app.database import engine, session_factory
from app.handlers import build_router
from app.middlewares.admin_menu_interrupt import AdminMenuInterruptMiddleware
from app.middlewares.db_session import DbSessionMiddleware
from app.middlewares.message_log import MessageLogMiddleware
from app.middlewares.message_log_session import MessageLogSessionMiddleware
from app.middlewares.metrics import MetricsMiddleware
from app.middlewares.rate_limit import RateLimitMiddleware
from app.middlewares.subscription import SubscriptionMiddleware
from app.middlewares.user_context import UserContextMiddleware
from app.observability.http_server import build_app, start_http_server
from app.services.broadcast_service import shutdown_jobs, start_broadcast_worker
from app.utils.i18n import load_translations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("kinobot")

_WEBHOOK_PATH = "/webhook"


def _init_sentry() -> None:
    """Sentry ixtiyoriy — DSN berilmagan bo'lsa jimgina o'tkazib yuboriladi."""
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.0)
        logger.info("Sentry yoqildi.")
    except ImportError:
        logger.warning("SENTRY_DSN berilgan, lekin sentry-sdk o'rnatilmagan.")


async def _make_storage(redis: Redis) -> BaseStorage:
    """Redis mavjud bo'lsa RedisStorage.

    Productionda Redis ishlamasa — FAIL FAST (ishga tushmaydi). Jimgina
    MemoryStorage'ga o'tish ko'p instansli deploymentda FSM holatini
    buzadi va restartda yo'qotadi, ya'ni "ishlayotgandek" ko'rinib, aslida
    sinib turgan bot beradi.
    """
    try:
        await redis.ping()
        logger.info("FSM uchun RedisStorage ishlatilmoqda.")
        return RedisStorage(redis)
    except Exception as exc:  # noqa: BLE001
        if settings.bot_env == "production":
            raise RuntimeError(
                "Redis mavjud emas — production rejimida ishga tushirib "
                "bo'lmaydi (FSM/rate-limit/kesh Redis'ga bog'liq). "
                f"Xato: {exc}"
            ) from exc
        logger.warning(
            "Redis mavjud emas (%s) — DEV rejimida MemoryStorage ishlatiladi.", exc
        )
        return MemoryStorage()


def _register_middlewares(dp: Dispatcher, redis: Redis) -> None:
    # Metrikalar — eng tashqi qatlam (butun pipeline o'lchovga kiradi).
    dp.update.outer_middleware(MetricsMiddleware())

    # DB sessiya — butun update'ni o'raydi.
    dp.update.outer_middleware(DbSessionMiddleware(session_factory))

    # Message va callback uchun kontekst zanjiri (ro'yxat tartibida ishlaydi).
    for observer in (dp.message, dp.callback_query):
        observer.middleware(UserContextMiddleware())
        observer.middleware(RateLimitMiddleware(redis))
        observer.middleware(SubscriptionMiddleware(redis))

    # Admin menyu tugmasi bosilsa — eski FSM oqimi matnni "yutib olmasin".
    # OUTER middleware SHART (oddiy .middleware() emas): aiogram avval har
    # bir handlerning filtrini tekshiradi va FAQAT filtr mos kelgandan
    # keyin ICHKI middleware'larni ishga tushiradi (Router.trigger() shunday
    # ishlaydi) — shu payt eski FSM holati allaqachon "yutib" ulgurgan
    # bo'ladi. Outer middleware esa filtr tekshiruvidan OLDIN ishlaydi,
    # shuning uchun holatni shu yerda tozalash real ta'sir qiladi.
    dp.message.outer_middleware(AdminMenuInterruptMiddleware())

    # "🧹 Suhbatni tozalash" uchun: HAR bir kiruvchi xabarni qayd etadi
    # (shu sabab ham OUTER — handler topilmasa ham qayd bo'lishi kerak).
    dp.message.outer_middleware(MessageLogMiddleware(redis))


def _log_startup_info(username: str, bot_id: int) -> None:
    logger.info("Bot ishga tushdi: @%s (id=%s)", username, bot_id)
    logger.info(
        "MODE=%s ENV=%s | STORAGE_CHANNEL_ID=%s | REQUIRED_CHANNELS=%s | ADMIN_IDS=%s",
        settings.bot_mode,
        settings.bot_env,
        settings.storage_channel_id,
        settings.required_channels,
        settings.admin_ids,
    )
    if settings.storage_channel_id == -1001234567890:
        logger.warning(
            "DIQQAT: STORAGE_CHANNEL_ID hali SOXTA (-1001234567890). "
            "Kanaldan avto qo'shish ISHLAMAYDI. Real kanal ID'sini .env ga yozing."
        )


async def _run_polling(bot: Bot, dp: Dispatcher) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def _run_webhook(bot: Bot, dp: Dispatcher, http_app) -> None:  # noqa: ANN001
    """Webhook: aiogram handlerini mavjud aiohttp ilovasiga ulaydi.

    Telegram'ning secret_token'i tekshiriladi — endpointga tashqaridan
    soxta so'rov yuborib bo'lmaydi.
    """
    if not settings.webhook_url:
        raise RuntimeError("BOT_MODE=webhook, lekin WEBHOOK_URL berilmagan.")

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.webhook_secret or None,
    ).register(http_app, path=_WEBHOOK_PATH)
    setup_application(http_app, dp, bot=bot)

    await bot.set_webhook(
        url=f"{settings.webhook_url.rstrip('/')}{_WEBHOOK_PATH}",
        secret_token=settings.webhook_secret or None,
        drop_pending_updates=True,
    )
    logger.info("Webhook o'rnatildi: %s%s", settings.webhook_url, _WEBHOOK_PATH)
    # HTTP server allaqachon ishlayapti — shu yerda cheksiz kutamiz.
    await asyncio.Event().wait()


async def main() -> None:
    load_translations()
    _init_sentry()

    redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=settings.redis_max_connections,
    )
    storage = await _make_storage(redis)

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties())
    # "🧹 Suhbatni tozalash" uchun: HAR bir chiquvchi Telegram API chaqiruvini
    # (qaysi handler yuborganidan qat'i nazar) ushlab, message_id'ni qayd etadi.
    bot.session.middleware(MessageLogSessionMiddleware(redis))
    dp = Dispatcher(storage=storage)

    # Handlerlarga qo'shimcha kontekst uzatamiz
    dp["redis"] = redis
    dp["session_factory"] = session_factory

    _register_middlewares(dp, redis)
    dp.include_router(build_router())

    http_app = build_app(engine, redis)
    runner = await start_http_server(http_app, settings.http_port)

    # Durable broadcast worker — DB'dagi joblarni oladi (restart-safe).
    start_broadcast_worker(bot, session_factory)

    try:
        me = await bot.get_me()
        _log_startup_info(me.username or "?", me.id)

        if settings.bot_mode == "webhook":
            await _run_webhook(bot, dp, http_app)
        else:
            await _run_polling(bot, dp)
    finally:
        await shutdown_jobs()
        await runner.cleanup()
        await bot.session.close()
        await redis.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
