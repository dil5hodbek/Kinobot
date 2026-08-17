"""Majburiy obuna tekshiruvi middleware."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User as TgUser
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.keyboards.inline import subscription_keyboard
from app.services.subscription_service import SubscriptionService
from app.utils.i18n import t

# Obuna tekshiruvidan ozod update'lar
_ALLOWED_COMMANDS = {"/start"}
_ALLOWED_CALLBACKS = {"check_subscription"}
_ALLOWED_CALLBACK_PREFIXES = ("lang:",)


class SubscriptionMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _is_exempt(self, event: TelegramObject) -> bool:
        if isinstance(event, Message):
            text = (event.text or "").strip()
            return any(text.startswith(cmd) for cmd in _ALLOWED_COMMANDS)
        if isinstance(event, CallbackQuery):
            data = event.data or ""
            if data in _ALLOWED_CALLBACKS:
                return True
            return any(data.startswith(p) for p in _ALLOWED_CALLBACK_PREFIXES)
        return False

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        session: AsyncSession | None = data.get("session")
        bot = data.get("bot")

        if tg_user is None or session is None or bot is None:
            return await handler(event, data)

        # Adminlar va ozod update'lar tekshirilmaydi
        if tg_user.id in settings.admin_ids or self._is_exempt(event):
            return await handler(event, data)

        lang = data.get("lang", settings.default_language)
        service = SubscriptionService(session, self._redis)
        unsubscribed = await service.get_unsubscribed(bot, tg_user.id)

        if not unsubscribed:
            return await handler(event, data)

        # Obuna yo'q — kanallar ekranini ko'rsatamiz
        keyboard = subscription_keyboard(unsubscribed, lang)
        text = t("subscribe_required", lang)
        if isinstance(event, Message):
            await event.answer(text, reply_markup=keyboard)
        elif isinstance(event, CallbackQuery):
            await event.answer()
            if event.message is not None:
                await event.message.answer(text, reply_markup=keyboard)
        return None
