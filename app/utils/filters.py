"""Maxsus aiogram filtrlari."""
from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.utils.i18n import button_matches


class IsAdmin(BaseFilter):
    """Foydalanuvchi ADMIN_IDS ichidami?"""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        return user is not None and user.id in settings.admin_ids


class ButtonText(BaseFilter):
    """Reply-tugma matnini (barcha tillarda) i18n kaliti bo'yicha aniqlaydi."""

    def __init__(self, key: str) -> None:
        self._key = key

    async def __call__(self, message: Message) -> bool:
        return button_matches(message.text, self._key)
