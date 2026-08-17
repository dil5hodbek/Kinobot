"""Testlar uchun umumiy yordamchilar: aiogram obyektlarini TARMOQSIZ yasash.

`Bot.session`ni `AsyncMock` bilan almashtiramiz — `.answer()`, `.get_chat_member()`
kabi metodlar haqiqiy aiogram kodini (validatsiya, method obyektlari) ishlatadi,
lekin tarmoqqa chiqmaydi. `bot.session.return_value` orqali javobni sozlash,
`bot.session.call_args` orqali qaysi Method (masalan SendMessage) va qanday
argumentlar bilan chaqirilganini tekshirish mumkin.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

from aiogram import Bot
from aiogram.types import CallbackQuery, Chat, Message
from aiogram.types import User as TgUser


def make_bot() -> Bot:
    bot = Bot(token="123456:TEST_TOKEN")
    bot.session = AsyncMock()
    return bot


def make_user(user_id: int) -> TgUser:
    return TgUser(id=user_id, is_bot=False, first_name="Test")


def make_message(
    bot: Bot, user_id: int, chat_id: int | None = None, text: str = "salom"
) -> Message:
    return Message.model_construct(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=Chat(id=chat_id or user_id, type="private"),
        from_user=make_user(user_id),
        text=text,
    ).as_(bot)


def make_callback(
    bot: Bot, user_id: int, data: str = "noop", chat_id: int | None = None
) -> CallbackQuery:
    message = make_message(bot, user_id, chat_id=chat_id, text="")
    return CallbackQuery.model_construct(
        id="1",
        from_user=make_user(user_id),
        chat_instance="ci",
        message=message,
        data=data,
    ).as_(bot)


class FakeZSetRedis:
    """redis.asyncio.Redis o'rniga — ZADD/ZRANGEBYSCORE/ZREMRANGEBYSCORE/DELETE/EXPIRE
    komandalarini xotirada simulyatsiya qiladi (chat_cleanup_service testlari uchun)."""

    def __init__(self) -> None:
        self._zsets: dict[str, dict[str, float]] = {}
        self.expired: dict[str, int] = {}

    async def zadd(self, key: str, mapping: dict[str, float]) -> None:
        self._zsets.setdefault(key, {}).update(mapping)

    async def zrangebyscore(self, key: str, min_score: float, max_score: float) -> list[str]:
        members = self._zsets.get(key, {})
        return [m for m, s in members.items() if min_score <= s <= max_score]

    async def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> None:
        members = self._zsets.get(key)
        if not members:
            return
        for member in [m for m, s in members.items() if min_score <= s <= max_score]:
            del members[member]

    async def delete(self, key: str) -> None:
        self._zsets.pop(key, None)
        self.expired.pop(key, None)

    async def expire(self, key: str, seconds: int) -> None:
        self.expired[key] = seconds


class BrokenRedis:
    """Har qanday chaqiruvda xato beradigan Redis — fail-open testlari uchun."""

    def __getattr__(self, _name: str):  # noqa: ANN001, ANN204
        async def _raise(*_args, **_kwargs):  # noqa: ANN002, ANN003
            raise ConnectionError("redis ishlamayapti")

        return _raise
