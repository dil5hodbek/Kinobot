"""Foydalanuvchilar bilan ishlovchi repository (barcha DB kirishlari shu yerda)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        username: str | None,
        full_name: str | None,
        language: str,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            language=language,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def touch_last_active(self, user_id: int) -> None:
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_active_at=datetime.now(timezone.utc))
        )

    async def set_language(self, telegram_id: int, language: str) -> None:
        await self._session.execute(
            update(User).where(User.telegram_id == telegram_id).values(language=language)
        )

    async def set_blocked(self, telegram_id: int, blocked: bool) -> None:
        await self._session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(is_blocked=blocked)
        )

    async def set_blocked_bulk(self, telegram_ids: list[int], blocked: bool = True) -> None:
        if not telegram_ids:
            return
        await self._session.execute(
            update(User)
            .where(User.telegram_id.in_(telegram_ids))
            .values(is_blocked=blocked)
        )

    async def get_active_telegram_ids(self) -> list[int]:
        """Broadcast uchun bloklanmagan foydalanuvchilar telegram_id lari."""
        result = await self._session.execute(
            select(User.telegram_id).where(User.is_blocked.is_(False))
        )
        return [row[0] for row in result.all()]

    async def count_total(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(User))
        return int(result.scalar_one())

    async def count_new_today(self) -> int:
        start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        result = await self._session.execute(
            select(func.count()).select_from(User).where(User.created_at >= start)
        )
        return int(result.scalar_one())

    async def count_active_since(self, days: int) -> int:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self._session.execute(
            select(func.count())
            .select_from(User)
            .where(User.last_active_at >= since)
        )
        return int(result.scalar_one())

    async def count_blocked(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(User).where(User.is_blocked.is_(True))
        )
        return int(result.scalar_one())
