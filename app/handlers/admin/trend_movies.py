"""Admin: '🔥 Trend kinolar' — trend ro'yxatini qo'lda boshqarish.

Trend endi ko'rishlar soniga avtomatik bog'liq emas (bu statistikada
"eng ko'p ko'rilgan" sifatida alohida qoladi) — admin bu yerdan kino
qo'shadi/o'chiradi, foydalanuvchiga esa ko'pi bilan `TREND_LIMIT`
(standart 10) tasi ko'rinadi.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.keyboards.inline import trend_admin_list_keyboard, trend_pick_keyboard
from app.services.movie_service import AddTrendResult, MovieService
from app.states.admin_states import TrendMovies
from app.utils.filters import ButtonText, IsAdmin
from app.utils.i18n import t

router = Router(name="admin_trend_movies")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def _show_list(message: Message, lang: str, service: MovieService) -> None:
    movies = await service.get_trending()
    if movies:
        await message.answer(
            t("trend_admin_title", lang, count=len(movies), limit=settings.trend_limit),
            reply_markup=trend_admin_list_keyboard(movies, lang),
        )
    else:
        await message.answer(t("trend_admin_empty", lang))


async def _add_and_report(
    message: Message, lang: str, service: MovieService, movie_id: int
) -> None:
    result = await service.add_to_trending(movie_id)
    if result is AddTrendResult.ADDED:
        await message.answer(t("trend_add_done", lang))
    elif result is AddTrendResult.ALREADY_TRENDING:
        await message.answer(t("trend_add_already", lang))
    elif result is AddTrendResult.LIMIT_REACHED:
        await message.answer(t("trend_add_full", lang, limit=settings.trend_limit))
    else:  # NOT_FOUND — kamdan-kam, masalan tanlangan orada kino o'chirilgan bo'lsa
        await message.answer(t("trend_add_not_found", lang))
    await _show_list(message, lang, service)


@router.message(StateFilter(None), ButtonText("btn_trend_movies"))
async def open_trend_movies(
    message: Message, lang: str, state: FSMContext, session: AsyncSession
) -> None:
    service = MovieService(session)
    await _show_list(message, lang, service)
    await state.set_state(TrendMovies.waiting_add_query)
    await message.answer(t("trend_add_ask", lang))


@router.message(TrendMovies.waiting_add_query)
async def got_trend_query(message: Message, lang: str, session: AsyncSession) -> None:
    query = (message.text or "").strip()
    if not query:
        return

    service = MovieService(session)
    lookup = await service.resolve_admin_query(query)

    if lookup.movie is not None:
        await _add_and_report(message, lang, service, lookup.movie.id)
        return
    if not lookup.candidates:
        await message.answer(t("trend_add_not_found", lang))
        return
    await message.answer(
        t("trend_pick", lang), reply_markup=trend_pick_keyboard(lookup.candidates, lang)
    )


@router.callback_query(F.data.startswith("trendpick:"))
async def pick_trend_movie(
    callback: CallbackQuery, lang: str, session: AsyncSession
) -> None:
    await callback.answer()
    try:
        movie_id = int((callback.data or "").split(":", 1)[1])
    except (ValueError, IndexError):
        return
    if callback.message is not None:
        await _add_and_report(callback.message, lang, MovieService(session), movie_id)


@router.callback_query(F.data.startswith("trendrm:"))
async def remove_trend_movie(
    callback: CallbackQuery, lang: str, session: AsyncSession
) -> None:
    await callback.answer()
    try:
        movie_id = int((callback.data or "").split(":", 1)[1])
    except (ValueError, IndexError):
        return

    service = MovieService(session)
    await service.remove_from_trending(movie_id)
    if callback.message is not None:
        await callback.message.answer(t("trend_removed", lang))
        await _show_list(callback.message, lang, service)
