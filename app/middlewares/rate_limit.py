"""Redis asosidagi flood-control — atomik token bucket (Lua).

Avvalgi INCR+EXPIRE fixed-window limiter chegara-burst muammosiga ega edi:
oyna almashish payti (12:00:59 → 12:01:00) foydalanuvchi limitning 2
baravarini yuborishi mumkin edi, INCR va EXPIRE ham ikki alohida chaqiriq
edi (EXPIRE o'tmay qolsa kalit abadiy qolardi). Token bucket:
  • sig'im  = RATE_LIMIT_PER_MINUTE (burst uchun);
  • to'lish = RATE_LIMIT_PER_MINUTE/60 token/soniya;
  • butun mantiq BITTA Lua skriptda — atomik, bir nechta bot instansi bilan
    ham to'g'ri (holat faqat Redis'da, jarayon xotirasida emas);
  • vaqt Redis serveridan olinadi (TIME) — instanslar orasidagi soat farqi
    ta'sir qilmaydi.
Redis ishlamasa — FAIL-OPEN (hech kim bloklanmaydi): mavjudlik qat'iylikdan
ustun (bot butunlay javobsiz bo'lib qolmasin).
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User as TgUser
from redis.asyncio import Redis

from app.config import settings
from app.utils.i18n import t

logger = logging.getLogger(__name__)

# KEYS[1] — bucket kaliti; ARGV[1] — sig'im; ARGV[2] — token/soniya.
# Qaytaradi: 1 = ruxsat, 0 = limit oshdi.
_TOKEN_BUCKET_LUA = """
local time = redis.call('TIME')
local now_ms = time[1] * 1000 + math.floor(time[2] / 1000)
local capacity = tonumber(ARGV[1])
local refill_per_sec = tonumber(ARGV[2])

local data = redis.call('HMGET', KEYS[1], 'tokens', 'ts')
local tokens = tonumber(data[1])
local ts = tonumber(data[2])
if tokens == nil then
    tokens = capacity
    ts = now_ms
end

local elapsed_sec = math.max(0, now_ms - ts) / 1000
tokens = math.min(capacity, tokens + elapsed_sec * refill_per_sec)

local allowed = 0
if tokens >= 1 then
    tokens = tokens - 1
    allowed = 1
end

redis.call('HSET', KEYS[1], 'tokens', tokens, 'ts', now_ms)
redis.call('PEXPIRE', KEYS[1], 180000)
return allowed
"""


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        if tg_user is None or tg_user.id in settings.admin_ids:
            return await handler(event, data)

        lang = data.get("lang", settings.default_language)
        key = f"rl:{tg_user.id}"
        capacity = settings.rate_limit_per_minute
        refill_per_sec = capacity / 60

        try:
            allowed = int(
                await self._redis.eval(
                    _TOKEN_BUCKET_LUA, 1, key, str(capacity), str(refill_per_sec)
                )
            )
        except Exception as exc:  # noqa: BLE001 - Redis ishlamasa cheklamaymiz
            logger.debug("Rate-limit Redis xatosi: %s", exc)
            return await handler(event, data)

        if not allowed:
            await self._notify(event, lang)
            return None

        return await handler(event, data)

    @staticmethod
    async def _notify(event: TelegramObject, lang: str) -> None:
        text = t("rate_limit", lang)
        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=False)
