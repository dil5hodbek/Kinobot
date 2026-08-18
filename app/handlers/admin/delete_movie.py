"""Admin: '🗑 O'chirish' — kino kodini/nomini so'rab, topib, butunlay o'chirish."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.inline import delete_confirm_keyboard, delete_results_keyboard
from app.models.movie import Movie
from app.services.audit_service import audit
from app.services.movie_service import MovieService
from app.states.admin_states import DeleteMovie
from app.utils.filters import ButtonText, IsAdmin
from app.utils.format import movie_title
from app.utils.i18n import t

router = Router(name="admin_delete_movie")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def _confirm_text(movie: Movie, lang: str) -> str:
    return t(
        "delete_confirm",
        lang,
        title=movie_title(movie, lang),
        code=movie.code,
        genre=movie.genre or t("unknown", lang),
        year=movie.year or t("unknown", lang),
        views=movie.views_count,
    )


@router.message(StateFilter(None), ButtonText("btn_delete_movie"))
async def start_delete(message: Message, lang: str, state: FSMContext) -> None:
    await state.set_state(DeleteMovie.waiting_query)
    await message.answer(t("delete_ask", lang))


@router.message(DeleteMovie.waiting_query)
async def got_query(
    message: Message, lang: str, state: FSMContext, session: AsyncSession
) -> None:
    query = (message.text or "").strip()
    if not query:
        return

    service = MovieService(session)
    lookup = await service.resolve_admin_query(query)

    if lookup.movie is not None:
        await state.clear()
        await message.answer(
            _confirm_text(lookup.movie, lang),
            reply_markup=delete_confirm_keyboard(lookup.movie.id, lang),
        )
        return
    if not lookup.candidates:
        await message.answer(t("delete_not_found", lang))
        return

    await state.clear()
    await message.answer(
        t("delete_pick", lang),
        reply_markup=delete_results_keyboard(lookup.candidates, lang),
    )


@router.callback_query(F.data.startswith("delpick:"))
async def pick_movie(
    callback: CallbackQuery, lang: str, session: AsyncSession
) -> None:
    await callback.answer()
    try:
        movie_id = int((callback.data or "").split(":", 1)[1])
    except (ValueError, IndexError):
        return

    movie = await MovieService(session).get_any_by_id(movie_id)
    if movie is None:
        if callback.message is not None:
            await _safe_edit(callback.message, t("delete_gone", lang))
        return

    if callback.message is not None:
        await _safe_edit(
            callback.message,
            _confirm_text(movie, lang),
            delete_confirm_keyboard(movie.id, lang),
        )


@router.callback_query(F.data.startswith("delyes:"))
async def confirm_delete(
    callback: CallbackQuery, lang: str, session: AsyncSession
) -> None:
    await callback.answer()
    try:
        movie_id = int((callback.data or "").split(":", 1)[1])
    except (ValueError, IndexError):
        return

    service = MovieService(session)
    movie = await service.get_any_by_id(movie_id)
    if movie is None:
        if callback.message is not None:
            await _safe_edit(callback.message, t("delete_gone", lang))
        return

    code = movie.code
    await service.delete_movie(movie.id)
    await audit(
        session,
        admin_id=callback.from_user.id,
        action="delete_movie",
        entity_type="movie",
        entity_id=movie_id,
        metadata=code,
    )
    if callback.message is not None:
        await _safe_edit(callback.message, t("delete_done", lang, code=code))


@router.callback_query(F.data == "delno")
async def cancel_delete(callback: CallbackQuery, lang: str) -> None:
    await callback.answer()
    if callback.message is not None:
        await _safe_edit(callback.message, t("delete_cancelled", lang))


async def _safe_edit(message: Message, text: str, markup=None) -> None:
    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramAPIError:
        # Matn o'zgarmagan yoki xabar eski bo'lsa — yangi xabar yuboramiz
        try:
            await message.answer(text, reply_markup=markup)
        except TelegramAPIError:
            pass
