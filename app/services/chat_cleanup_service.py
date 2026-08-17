"""'Suhbatni tozalash' — so'nggi 48 soatlik xabarlarni kuzatish va o'chirish.

Telegram Bot API faqat 48 soatdan yosh xabarlarni o'chirishga ruxsat beradi
(bundan qat'iy nazar yo'q) va botga "shu chat'ning butun tarixini ber" degan
metod bermaydi — shuning uchun har bir xabar (kiruvchi HAM, chiquvchi HAM)
yuborilgan/kelgan zahoti Redis'da ZSET (score=vaqt, member=message_id)
sifatida qayd etiladi (qarang: app/middlewares/message_log.py va
app/middlewares/message_log_session.py). "Tozalash" bosilganda shu ro'yxat
o'qiladi va xabarlar birma-bir o'chiriladi.
"""
from __future__ import annotations

import asyncio
import logging
import time

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 48 * 60 * 60
_KEY_TTL_SECONDS = WINDOW_SECONDS + 60 * 60  # bo'sh chat kaliti o'zi tozalanib tursin
_DELETE_CHUNK_SIZE = 100  # Bot API deleteMessages bir chaqiruvda 1-100 ta id qabul qiladi
_CHUNK_DELAY = 0.05  # Telegram flood-limitidan xavfsizlik uchun (chunklar orasida)


def _key(chat_id: int) -> str:
    return f"chatlog:{chat_id}"


async def log_message(redis: Redis, chat_id: int, message_id: int) -> None:
    """Xabarni keyingi "Tozalash" uchun ro'yxatga oladi (best-effort, Redis
    ishlamasa ham bot davom etaveradi — kuzatuv shart emas)."""
    now = time.time()
    key = _key(chat_id)
    try:
        await redis.zadd(key, {str(message_id): now})
        await redis.zremrangebyscore(key, 0, now - WINDOW_SECONDS)
        await redis.expire(key, _KEY_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Xabar kuzatuvi (log_message) xatosi: %s", exc)


async def pop_recent_message_ids(redis: Redis, chat_id: int) -> list[int]:
    """So'nggi 48 soatdagi xabar ID'larini qaytaradi va ro'yxatni bo'shatadi."""
    key = _key(chat_id)
    now = time.time()
    try:
        raw_ids = await redis.zrangebyscore(key, now - WINDOW_SECONDS, now)
        await redis.delete(key)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Xabar ro'yxatini o'qishda xato: %s", exc)
        return []
    return [int(raw_id) for raw_id in raw_ids]


async def delete_messages(bot: Bot, chat_id: int, message_ids: list[int]) -> int:
    """Berilgan xabarlarni ommaviy (`deleteMessages`, 100 tadan bir chaqiruvda)
    o'chiradi — bitta-bitta `deleteMessage` chaqirishdan ancha tezroq katta
    tarix uchun. Qaytgan son — nechta xabar SO'RALGANI (Telegram allaqachon
    yo'q/48 soatdan eski xabarlarni chaqiruv ichida jimgina o'tkazib
    yuboradi, buni alohida bildirmaydi — shuning uchun aniq emas, taxminiy)."""
    deleted = 0
    for i in range(0, len(message_ids), _DELETE_CHUNK_SIZE):
        chunk = message_ids[i : i + _DELETE_CHUNK_SIZE]
        try:
            await bot.delete_messages(chat_id, chunk)
            deleted += len(chunk)
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await bot.delete_messages(chat_id, chunk)
                deleted += len(chunk)
            except TelegramAPIError:
                pass
        except TelegramAPIError:
            pass
        await asyncio.sleep(_CHUNK_DELAY)
    return deleted
