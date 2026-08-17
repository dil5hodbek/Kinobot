"""Majburiy obuna kanallari biznes logikasi (CRUD + bot-admin tekshiruvi)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.required_channel import RequiredChannel
from app.repositories.channel_repository import ChannelRepository

logger = logging.getLogger(__name__)

_ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


class AddChannelResult(Enum):
    """Kanal qo'shish urinishi natijasi."""

    NOT_ADMIN = auto()  # bot kanalda admin emas / kanal topilmadi
    ALREADY_EXISTS = auto()  # shu username allaqachon ro'yxatda
    ADDED = auto()


@dataclass(frozen=True, slots=True)
class AddChannelOutcome:
    result: AddChannelResult
    channel: RequiredChannel | None = None


class ChannelService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ChannelRepository(session)

    async def list_active(self) -> list[RequiredChannel]:
        return await self._repo.get_active()

    async def add_channel(self, bot: Bot, username: str) -> AddChannelOutcome:
        """Bot kanalda admin ekanini tekshiradi, mavjud bo'lmasa qo'shadi."""
        title, invite_link = await self._verify_bot_admin(bot, username)
        if title is None:
            return AddChannelOutcome(AddChannelResult.NOT_ADMIN)

        if await self._repo.get_by_username(username) is not None:
            return AddChannelOutcome(AddChannelResult.ALREADY_EXISTS)

        channel = await self._repo.create(
            channel_username=username,
            channel_title=title,
            invite_link=invite_link,
        )
        return AddChannelOutcome(AddChannelResult.ADDED, channel)

    async def remove_channel(self, channel_id: int) -> bool:
        """Kanalni faolsizlantiradi. Topilsa True, aks holda False."""
        channel = await self._repo.get_by_id(channel_id)
        if channel is None:
            return False
        await self._repo.deactivate(channel_id)
        return True

    @staticmethod
    async def _verify_bot_admin(
        bot: Bot, username: str
    ) -> tuple[str | None, str | None]:
        """Bot kanalda admin ekanini tekshiradi. (title, invite_link) qaytaradi."""
        try:
            chat = await bot.get_chat(f"@{username}")
            member = await bot.get_chat_member(chat.id, bot.id)
            if member.status not in _ADMIN_STATUSES:
                return None, None
        except TelegramAPIError as exc:
            logger.warning("Kanal tekshiruvi xatosi (@%s): %s", username, exc)
            return None, None

        invite_link = chat.invite_link
        if invite_link is None:
            try:
                invite_link = await bot.export_chat_invite_link(chat.id)
            except TelegramAPIError:
                invite_link = None

        return (chat.title or username), invite_link
