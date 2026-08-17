"""Majburiy obuna tekshiruvi (getChatMember + Redis kesh)."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.channel_repository import ChannelRepository

logger = logging.getLogger(__name__)

_SUBSCRIBED_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
}
_CACHE_TTL = 60  # soniya


@dataclass(slots=True)
class ChannelInfo:
    username: str
    title: str | None
    invite_link: str | None

    @property
    def url(self) -> str:
        if self.invite_link:
            return self.invite_link
        return f"https://t.me/{self.username}"

    @property
    def display(self) -> str:
        return self.title or f"@{self.username}"


class SubscriptionService:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self._session = session
        self._redis = redis
        self._channel_repo = ChannelRepository(session)

    async def _all_channels(self) -> list[ChannelInfo]:
        """.env va DB kanallarini birlashtiradi (username bo'yicha unikal)."""
        channels: dict[str, ChannelInfo] = {}
        for username in settings.required_channels:
            channels[username] = ChannelInfo(username=username, title=None, invite_link=None)

        for ch in await self._channel_repo.get_active():
            channels[ch.channel_username] = ChannelInfo(
                username=ch.channel_username,
                title=ch.channel_title,
                invite_link=ch.invite_link,
            )
        return list(channels.values())

    async def _is_subscribed(self, bot: Bot, username: str, user_id: int) -> bool:
        cache_key = f"sub:{username}:{user_id}"
        cached = await self._safe_cache_get(cache_key)
        if cached is not None:
            return cached == "1"

        try:
            member = await bot.get_chat_member(f"@{username}", user_id)
            subscribed = member.status in _SUBSCRIBED_STATUSES
        except TelegramAPIError as exc:
            # Kanal topilmasa yoki bot admin bo'lmasa — bloklamaymiz (True)
            logger.warning("Obuna tekshirib bo'lmadi (@%s): %s", username, exc)
            subscribed = True

        await self._safe_cache_set(cache_key, "1" if subscribed else "0")
        return subscribed

    async def get_unsubscribed(self, bot: Bot, user_id: int) -> list[ChannelInfo]:
        """Foydalanuvchi obuna bo'lmagan kanallar ro'yxati.

        Har bir kanal tekshiruvi PARALLEL ishlaydi (kesh sovub qolganda har
        biri alohida Telegram API chaqiruvi bo'lishi mumkin — ketma-ket
        bo'lsa, kanallar soniga chiziqli proporsional kutish vaqti bo'lardi,
        bu esa har bir oddiy xabar uchun ishlaydigan obuna filtrida sezilarli).
        """
        channels = await self._all_channels()
        subscribed_flags = await asyncio.gather(
            *(self._is_subscribed(bot, ch.username, user_id) for ch in channels)
        )
        return [ch for ch, subscribed in zip(channels, subscribed_flags) if not subscribed]

    async def is_fully_subscribed(self, bot: Bot, user_id: int) -> bool:
        return len(await self.get_unsubscribed(bot, user_id)) == 0

    async def list_channels(self) -> list[ChannelInfo]:
        return await self._all_channels()

    async def channels_with_status(
        self, bot: Bot, user_id: int
    ) -> list[tuple[ChannelInfo, bool]]:
        """Har bir kanal + shu foydalanuvchi unga obuna bo'lganmi (✅/➕ belgisi
        uchun, "Kanallar" ro'yxatida)."""
        channels = await self._all_channels()
        subscribed_flags = await asyncio.gather(
            *(self._is_subscribed(bot, ch.username, user_id) for ch in channels)
        )
        return list(zip(channels, subscribed_flags))

    async def _safe_cache_get(self, key: str) -> str | None:
        try:
            return await self._redis.get(key)
        except Exception as exc:  # noqa: BLE001 - kesh ishlamasa ham davom etamiz
            logger.debug("Redis get xatosi: %s", exc)
            return None

    async def _safe_cache_set(self, key: str, value: str) -> None:
        try:
            await self._redis.set(key, value, ex=_CACHE_TTL)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Redis set xatosi: %s", exc)
