"""Foydalanuvchini yaratadi/oladi va data ga user + lang qo'shadi."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import UserService


class UserContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        session: AsyncSession | None = data.get("session")

        if tg_user is None or session is None or tg_user.is_bot:
            return await handler(event, data)

        service = UserService(session)
        user, is_new = await service.get_or_create(
            telegram_id=tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name,
        )

        data["user"] = user
        data["lang"] = user.language
        data["is_new_user"] = is_new
        return await handler(event, data)
