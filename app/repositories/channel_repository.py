"""Majburiy obuna kanallari repository (dinamik boshqarish)."""
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.required_channel import RequiredChannel


class ChannelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active(self) -> list[RequiredChannel]:
        result = await self._session.execute(
            select(RequiredChannel)
            .where(RequiredChannel.is_active.is_(True))
            .order_by(RequiredChannel.id)
        )
        return list(result.scalars().all())

    async def get_by_username(self, username: str) -> RequiredChannel | None:
        result = await self._session.execute(
            select(RequiredChannel).where(
                RequiredChannel.channel_username == username
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, channel_id: int) -> RequiredChannel | None:
        result = await self._session.execute(
            select(RequiredChannel).where(RequiredChannel.id == channel_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        channel_username: str,
        channel_title: str | None,
        invite_link: str | None,
    ) -> RequiredChannel:
        channel = RequiredChannel(
            channel_username=channel_username,
            channel_title=channel_title,
            invite_link=invite_link,
        )
        self._session.add(channel)
        await self._session.flush()
        return channel

    async def deactivate(self, channel_id: int) -> None:
        await self._session.execute(
            update(RequiredChannel)
            .where(RequiredChannel.id == channel_id)
            .values(is_active=False)
        )
