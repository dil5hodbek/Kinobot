"""Trend kinolar tugmasi."""
from __future__ import annotations

from aiogram import Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.inline import trend_keyboard
from app.models.movie import Movie
from app.services.movie_service import MovieService
from app.utils.filters import ButtonText
from app.utils.format import movie_title
from app.utils.i18n import t

router = Router(name="trend")


def _trend_text(movies: list[Movie], lang: str) -> str:
    """Nomi + kod bilan ro'yxat (tugmalarda faqat kod ko'rinadi — tez tanlash uchun)."""
    lines = [
        t("trend_list_line", lang, idx=idx, title=movie_title(movie, lang), code=movie.code)
        for idx, movie in enumerate(movies, start=1)
    ]
    return t("trend_title", lang) + "\n\n" + "\n".join(lines)


@router.message(ButtonText("btn_trend"))
async def show_trend(message: Message, lang: str, session: AsyncSession) -> None:
    service = MovieService(session)
    movies = await service.get_trending()

    if not movies:
        await message.answer(t("trend_empty", lang))
        return

    await message.answer(_trend_text(movies, lang), reply_markup=trend_keyboard(movies))
