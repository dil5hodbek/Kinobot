"""Botning barcha CHIQUVCHI xabarlarini Redis'da qayd etadi ('Tozalash' uchun).

Bu Dispatcher middleware emas — aiogram Bot SESSION middleware'i
(`bot.session.middleware(...)` orqali ro'yxatga olinadi). Farqi: bu HAR BIR
Telegram API chaqiruvini ushlab turadi (qaysi handler yuborganidan qat'i
nazar — message.answer(), bot.send_message(), bot.copy_message(), broadcast
va h.k.), shuning uchun har bir joyda alohida qayd qilib yurish shart
bo'lmaydi — bitta joyda barchasi qamrab olinadi.
"""
from __future__ import annotations

from typing import Any

from aiogram import Bot
from aiogram.client.session.middlewares.base import (
    BaseRequestMiddleware,
    NextRequestMiddlewareType,
)
from aiogram.methods import TelegramMethod
from aiogram.methods.base import TelegramType
from redis.asyncio import Redis

from app.services.chat_cleanup_service import log_message


class MessageLogSessionMiddleware(BaseRequestMiddleware):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Any:
        result = await make_request(bot, method)

        message_id = getattr(result, "message_id", None)
        chat_id = getattr(method, "chat_id", None)
        if message_id is not None and isinstance(chat_id, int):
            await log_message(self._redis, chat_id, int(message_id))

        return result
