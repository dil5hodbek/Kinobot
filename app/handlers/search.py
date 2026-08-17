"""Qidiruv: kod/nom bo'yicha, natijalar va kino yuborish."""
from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.keyboards.inline import genre_movies_keyboard, search_results_keyboard
from app.models.user import User
from app.services.movie_service import MovieDeliveryError, MovieService
from app.utils.filters import ButtonText
from app.utils.i18n import t

router = Router(name="search")

_CODE_RE = re.compile(r"^\d{1,10}$")
_MAX_QUERY_LEN = 100


@router.message(ButtonText("btn_search"))
async def search_prompt(message: Message, lang: str) -> None:
    await message.answer(t("search_prompt", lang))


@router.callback_query(F.data.startswith("movie:"))
async def send_selected_movie(
    callback: CallbackQuery,
    user: User,
    lang: str,
    session: AsyncSession,
) -> None:
    await callback.answer()
    try:
        movie_id = int((callback.data or "").split(":", 1)[1])
    except (ValueError, IndexError):
        return

    service = MovieService(session)
    movie = await service.get_by_id(movie_id)
    if movie is None or callback.message is None:
        if callback.message is not None:
            await callback.message.answer(t("not_found", lang))
        return

    try:
        await service.deliver(
            callback.bot, movie, user.id, callback.message.chat.id, lang
        )
    except MovieDeliveryError:
        await callback.message.answer(
            t("movie_unavailable", lang, admin_phone=settings.admin_phone)
        )


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_search(
    message: Message,
    user: User,
    lang: str,
    session: AsyncSession,
) -> None:
    query = (message.text or "").strip()
    if not query:
        return
    if len(query) > _MAX_QUERY_LEN:
        query = query[:_MAX_QUERY_LEN]

    service = MovieService(session)

    # 1) Kod bo'yicha aniq qidiruv (kod raqam yoki matn bo'lishi mumkin —
    # admin har qanday kod kiritishi mumkin, shuning uchun formatidan
    # qat'i nazar avval aniq moslikni tekshiramiz).
    movie = await service.find_by_code(query)
    if movie is not None:
        await _deliver_or_warn(message, service, movie, user, lang)
        return
    if _CODE_RE.match(query):
        # Sof raqam aniq kod urinishi edi — topilmasa matnli/janr
        # qidiruvga o'tmaymiz (raqam kino nomiga tasodifiy mos kelmasin).
        await message.answer(t("not_found", lang))
        return

    # 2) Janr nomiga ANIQ mos kelsa (masalan "romance") — shu janrdagi
    # kinolar ro'yxati. Fuzzy nom qidiruvdan OLDIN tekshiriladi: janr
    # nomlari kichik, barqaror to'plam (kino nomi bilan chalkashish
    # ehtimoli past), aniq moslik esa foydalanuvchi kutgan natijani
    # kafolatlaydi (fuzzy bo'lsa noaniq/tasodifiy janr tanlanishi mumkin edi).
    genre = await service.match_genre(query)
    if genre is not None:
        movies = await service.movies_by_genre(genre)
        if movies:
            await message.answer(
                t("genre_movies_title", lang, genre=genre),
                reply_markup=genre_movies_keyboard(movies, lang),
            )
            return

    # 3) Matn bo'yicha fuzzy qidiruv
    movies = await service.search(query)
    if not movies:
        await message.answer(t("not_found", lang))
        return

    if len(movies) == 1:
        await _deliver_or_warn(message, service, movies[0], user, lang)
        return

    await message.answer(
        t("multiple_found", lang),
        reply_markup=search_results_keyboard(movies, lang),
    )


async def _deliver_or_warn(
    message: Message,
    service: MovieService,
    movie,
    user: User,
    lang: str,
) -> None:
    try:
        await service.deliver(message.bot, movie, user.id, message.chat.id, lang)
    except MovieDeliveryError:
        await message.answer(
            t("movie_unavailable", lang, admin_phone=settings.admin_phone)
        )
