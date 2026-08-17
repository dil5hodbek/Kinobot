"""Kino biznes logikasi: qidiruv, yuborish, trend, statistika."""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.movie import Movie
from app.repositories.movie_repository import MovieRepository
from app.utils.format import movie_title
from app.utils.i18n import t

logger = logging.getLogger(__name__)


class MovieDeliveryError(Exception):
    """Video yuborib bo'lmadi (o'chirilgan yoki huquq yo'q)."""


class MovieService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MovieRepository(session)

    async def find_by_code(self, code: str) -> Movie | None:
        return await self._repo.get_active_by_code(code)

    async def find_by_code_any(self, code: str) -> Movie | None:
        """Faol yoki nofaol kino (admin tahrirlash uchun)."""
        return await self._repo.get_by_code_any(code)

    async def search(self, query: str) -> list[Movie]:
        return await self._repo.search_by_title(
            query=query,
            threshold=settings.search_similarity_threshold,
            limit=10,
        )

    async def get_by_id(self, movie_id: int) -> Movie | None:
        movie = await self._repo.get_by_id(movie_id)
        if movie is None or not movie.is_active:
            return None
        return movie

    async def get_any_by_id(self, movie_id: int) -> Movie | None:
        """Faol yoki nofaol kino (admin o'chirish/tahrirlash uchun)."""
        return await self._repo.get_by_id(movie_id)

    async def get_trending(self) -> list[Movie]:
        return await self._repo.get_trending(settings.trend_limit)

    async def get_all_movies(self) -> list[Movie]:
        """Barcha kinolar, kod bo'yicha raqamli-aware tartiblangan (hisobot uchun)."""
        movies = await self._repo.get_all(include_inactive=True)

        def sort_key(m: Movie) -> tuple[int, int, str]:
            # Avval raqamli kodlar (o'sish tartibida), so'ng matnli kodlar
            if m.code.isdigit():
                return (0, int(m.code), "")
            return (1, 0, m.code.lower())

        return sorted(movies, key=sort_key)

    def title_for(self, movie: Movie, lang: str) -> str:
        """Foydalanuvchi tiliga mos nom (bo'sh bo'lsa uz'ga qaytadi)."""
        return movie_title(movie, lang)

    def caption_for(self, movie: Movie, lang: str) -> str:
        return t(
            "movie_caption",
            lang,
            title=self.title_for(movie, lang),
            year=movie.year or t("unknown", lang),
            genre=movie.genre or t("unknown", lang),
            code=movie.code,
            views=movie.views_count,
        )

    async def deliver(
        self, bot: Bot, movie: Movie, user_db_id: int, chat_id: int, lang: str
    ) -> None:
        """copy_message orqali videoni yuboradi, ko'rishni hisoblaydi.

        Xato bo'lsa MovieDeliveryError ko'taradi va kinoni faolsizlantiradi.
        """
        try:
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=movie.channel_id,
                message_id=movie.message_id,
                caption=self.caption_for(movie, lang),
                protect_content=settings.protect_content,
            )
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            logger.warning(
                "Kino yuborib bo'lmadi (movie_id=%s): %s", movie.id, exc
            )
            await self._repo.deactivate(movie.id)
            await self._notify_admins_dead_link(bot, movie, exc)
            raise MovieDeliveryError(str(exc)) from exc

        # Ko'rish muvaffaqiyatli — statistika
        await self._repo.increment_views(movie.id)
        await self._repo.add_view(user_db_id, movie.id)

    @staticmethod
    async def _notify_admins_dead_link(
        bot: Bot, movie: Movie, exc: Exception
    ) -> None:
        """Video yuborilmagach adminlarni ogohlantiradi (spec 10.6)."""
        text = (
            f"⚠️ Kino yuborib bo'lmadi va faolsizlantirildi.\n"
            f"Kod: {movie.code}\nNomi: {movie.title_uz}\n"
            f"channel_id: {movie.channel_id} | message_id: {movie.message_id}\n"
            f"Sabab: {exc}"
        )
        for admin_id in settings.admin_ids:
            try:
                await bot.send_message(admin_id, text)
            except TelegramAPIError:
                continue

    async def add_movie(
        self,
        *,
        code: str,
        channel_id: int,
        message_id: int,
        title_uz: str,
        title_ru: str | None,
        title_en: str | None,
        year: int | None,
        genre: str | None,
    ) -> Movie:
        return await self._repo.create(
            code=code,
            channel_id=channel_id,
            message_id=message_id,
            title_uz=title_uz,
            title_ru=title_ru,
            title_en=title_en,
            year=year,
            genre=genre,
        )

    async def code_exists(self, code: str) -> bool:
        return await self._repo.get_by_code_any(code) is not None

    async def get_by_channel_message(
        self, channel_id: int, message_id: int
    ) -> Movie | None:
        return await self._repo.get_by_channel_message(channel_id, message_id)

    async def next_auto_code(self) -> str:
        return await self._repo.next_auto_code()

    async def deactivate(self, movie_id: int) -> None:
        await self._repo.deactivate(movie_id)

    async def delete_movie(self, movie_id: int) -> None:
        """Kinoni butunlay o'chiradi (kod bo'shaydi)."""
        await self._repo.delete(movie_id)

    async def update_fields(self, movie_id: int, **fields: object) -> None:
        await self._repo.update_fields(movie_id, **fields)
