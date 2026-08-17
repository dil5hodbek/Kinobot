"""Trend kinolar tugmasi."""
from __future__ import annotations

from aiogram import Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.inline import trend_keyboard
from app.services.movie_service import MovieService
from app.utils.filters import ButtonText
from app.utils.i18n import t

router = Router(name="trend")


@router.message(ButtonText("btn_trend"))
async def show_trend(message: Message, lang: str, session: AsyncSession) -> None:
    service = MovieService(session)
    movies = await service.get_trending()

    if not movies:
        await message.answer(t("trend_empty", lang))
        return

    await message.answer(
        t("trend_title", lang), reply_markup=trend_keyboard(movies, lang)
    )
