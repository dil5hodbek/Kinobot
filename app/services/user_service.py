"""Foydalanuvchi biznes logikasi."""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.i18n import SUPPORTED_LANGUAGES


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UserRepository(session)

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None,
        full_name: str | None,
    ) -> tuple[User, bool]:
        """
        Foydalanuvchini oladi yoki yaratadi. (user, is_new) qaytaradi.

        Yangi foydalanuvchidan ikkita update deyarli bir vaqtda kelsa (masalan
        /start ikki marta bosilsa), ikkalasi ham "user yo'q" deb ko'rib
        yaratishga urinishi mumkin. INSERT'ni SAVEPOINT (begin_nested) ichiga
        olamiz: ikkinchi INSERT birinchisi commit bo'lguncha PostgreSQL
        tomonidan bloklanadi, keyin unique constraint xatosi bilan
        qaytadi — buni ushlab, allaqachon yaratilgan qatorni o'qib olamiz.
        Bu YO'Q bo'lsa, butun update IntegrityError bilan yiqilib, javob
        yuborilmay qolardi.
        """
        user = await self._repo.get_by_telegram_id(telegram_id)
        if user is not None:
            await self._repo.touch_last_active(user.id)
            return user, False

        try:
            async with self._session.begin_nested():
                user = await self._repo.create(
                    telegram_id=telegram_id,
                    username=username,
                    full_name=full_name,
                    language=settings.default_language,
                )
        except IntegrityError:
            user = await self._repo.get_by_telegram_id(telegram_id)
            if user is None:
                raise
            await self._repo.touch_last_active(user.id)
            return user, False

        return user, True

    async def get(self, telegram_id: int) -> User | None:
        return await self._repo.get_by_telegram_id(telegram_id)

    async def set_language(self, telegram_id: int, language: str) -> None:
        if language not in SUPPORTED_LANGUAGES:
            language = settings.default_language
        await self._repo.set_language(telegram_id, language)

    async def mark_blocked(self, telegram_id: int, blocked: bool = True) -> None:
        await self._repo.set_blocked(telegram_id, blocked)
