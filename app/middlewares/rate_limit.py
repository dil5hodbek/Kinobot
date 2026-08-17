"""Redis asosidagi flood-control (foydalanuvchi uchun daqiqasiga limit)."""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User as TgUser
from redis.asyncio import Redis

from app.config import settings
from app.utils.i18n import t

logger = logging.getLogger(__name__)


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

        try:
            current = await self._redis.incr(key)
            if current == 1:
                await self._redis.expire(key, 60)
        except Exception as exc:  # noqa: BLE001 - Redis ishlamasa cheklamaymiz
            logger.debug("Rate-limit Redis xatosi: %s", exc)
            return await handler(event, data)

        if current > settings.rate_limit_per_minute:
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
