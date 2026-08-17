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
from app.keyboards.inline import movie_link_keyboard
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
        """Kinoni yuboradi (manba turiga qarab), ko'rishni hisoblaydi.

        Xato bo'lsa MovieDeliveryError ko'taradi.
        """
        if movie.source_type == "link":
            await self._deliver_link(bot, movie, chat_id, lang)
        else:
            await self._deliver_channel(bot, movie, chat_id, lang)

        # Ko'rish muvaffaqiyatli — statistika
        await self._repo.increment_views(movie.id)
        await self._repo.add_view(user_db_id, movie.id)

    async def _deliver_channel(
        self, bot: Bot, movie: Movie, chat_id: int, lang: str
    ) -> None:
        """copy_message orqali kanaldagi videoni yuboradi.

        Xato — manba post o'chirilgan yoki bot huquqi yo'qolgan degani
        (doimiy muammo, keyingi HAR BIR foydalanuvchida ham takrorlanadi) —
        shuning uchun kino FAOLSIZLANTIRILADI va adminlarga xabar beriladi.
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

    async def _deliver_link(
        self, bot: Bot, movie: Movie, chat_id: int, lang: str
    ) -> None:
        """Tashqi havolani tugma bilan yuboradi (video ko'chirilmaydi).

        Xato bo'lsa (masalan foydalanuvchi botni bloklagan) MUAMMO
        FOYDALANUVCHIDA, havolada emas — shuning uchun kino FAOLSIZLANTIRILMAYDI
        (_deliver_channel'dan farqli, bu yerda "manba o'chirilgan" degan
        signal umuman yo'q — Telegram xatosi faqat yetkazishga tegishli).
        """
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=self.caption_for(movie, lang),
                reply_markup=movie_link_keyboard(movie.external_url, lang),
            )
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            logger.warning(
                "Link kino yuborib bo'lmadi (movie_id=%s): %s", movie.id, exc
            )
            raise MovieDeliveryError(str(exc)) from exc

    @staticmethod
    async def _notify_admins_dead_link(
        bot: Bot, movie: Movie, exc: Exception
    ) -> None:
        """Video yuborilmagach adminlarni ogohlantiradi (spec 10.6)."""
        text = t(
            "dead_link_alert",
            settings.default_language,
            code=movie.code,
            title=movie.title_uz,
            channel_id=movie.channel_id,
            message_id=movie.message_id,
            reason=str(exc),
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
        title_uz: str,
        title_ru: str | None,
        title_en: str | None,
        year: int | None,
        genre: str | None,
        channel_id: int | None = None,
        message_id: int | None = None,
    ) -> Movie:
        """Kanaldan kino qo'shadi (source_type='channel', standart)."""
        return await self._repo.create(
            code=code,
            source_type="channel",
            channel_id=channel_id,
            message_id=message_id,
            title_uz=title_uz,
            title_ru=title_ru,
            title_en=title_en,
            year=year,
            genre=genre,
        )

    async def add_link_movie(
        self,
        *,
        code: str,
        external_url: str,
        title_uz: str,
        title_ru: str | None,
        title_en: str | None,
        year: int | None,
        genre: str | None,
    ) -> Movie:
        """Tashqi havola orqali kino qo'shadi (source_type='link')."""
        return await self._repo.create(
            code=code,
            source_type="link",
            external_url=external_url,
            title_uz=title_uz,
            title_ru=title_ru,
            title_en=title_en,
            year=year,
            genre=genre,
        )

    async def match_genre(self, query: str) -> str | None:
        """Kiritilgan matn mavjud janrlardan biriga ANIQ mos keladimi?

        Case-insensitive aniq moslik (masalan "romance" == "Romance").
        Moslik topilmasa None — chaqiruvchi (search.py) oddiy nom qidiruvга
        o'tadi. Bu haydovchi/foydalanuvchi so'zlarini kino nomi bilan
        chalkashtirmaslik uchun ATAYLAB "aniq" (fuzzy emas).
        """
        q = query.strip().lower()
        if not q:
            return None
        for genre in await self._repo.list_genres():
            if genre.strip().lower() == q:
                return genre
        return None

    async def movies_by_genre(self, genre: str) -> list[Movie]:
        return await self._repo.get_by_genre(genre)

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
