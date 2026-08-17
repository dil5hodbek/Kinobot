"""Har bir KIRUVCHI xabarni Redis'da qayd etadi ('Tozalash' funksiyasi uchun).

OUTER middleware sifatida ro'yxatga olinishi kerak (`dp.message.outer_middleware`):
inner middleware faqat biror handler filtri mos kelgandan keyin ishga
tushadi (qarang: app/middlewares/admin_menu_interrupt.py'dagi izoh), lekin
biz HAR BIR xabarni — hatto hech qanday handler ushlamaganini ham —
"tarix" sifatida qayd etishimiz kerak.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from redis.asyncio import Redis

from app.services.chat_cleanup_service import log_message


class MessageLogMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            await log_message(self._redis, event.chat.id, event.message_id)
        return await handler(event, data)
