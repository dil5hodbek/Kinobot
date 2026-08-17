"""Admin: kino tahrirlash / soft-delete FSM oqimi."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.inline import edit_movie_keyboard
from app.keyboards.reply import admin_menu_keyboard
from app.services.movie_service import MovieService
from app.states.admin_states import EditMovie
from app.utils.filters import ButtonText, IsAdmin
from app.utils.format import movie_title
from app.utils.i18n import t

router = Router(name="admin_edit_movie")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

_FIELD_COLUMN = {"title": "title_uz", "year": "year", "genre": "genre"}


@router.message(StateFilter(None), ButtonText("btn_edit_movie"))
async def start_edit(message: Message, lang: str, state: FSMContext) -> None:
    await state.set_state(EditMovie.waiting_code)
    await message.answer(t("edit_ask_code", lang))


@router.message(EditMovie.waiting_code)
async def got_edit_code(
    message: Message, lang: str, state: FSMContext, session: AsyncSession
) -> None:
    code = (message.text or "").strip()
    service = MovieService(session)
    movie = await service.find_by_code_any(code)
    if movie is None:
        await message.answer(t("edit_not_found", lang))
        return

    await state.update_data(movie_id=movie.id)
    await state.set_state(EditMovie.choosing_field)
    await message.answer(
        t("edit_menu", lang, title=movie_title(movie, lang), code=movie.code),
        reply_markup=edit_movie_keyboard(movie.id, lang),
    )


@router.callback_query(EditMovie.choosing_field, F.data.startswith("edit:"))
async def choose_field(
    callback: CallbackQuery, lang: str, state: FSMContext, session: AsyncSession
) -> None:
    await callback.answer()
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        return
    _, field, raw_id = parts
    try:
        movie_id = int(raw_id)
    except ValueError:
        return

    if field not in _FIELD_COLUMN:
        return

    await state.update_data(movie_id=movie_id, field=field)
    await state.set_state(EditMovie.waiting_value)
    if callback.message is not None:
        await callback.message.answer(t("edit_ask_new_value", lang))


@router.message(EditMovie.waiting_value)
async def got_new_value(
    message: Message, lang: str, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    movie_id = data.get("movie_id")
    field = data.get("field")
    if movie_id is None or field not in _FIELD_COLUMN:
        await state.clear()
        return

    raw = (message.text or "").strip()
    column = _FIELD_COLUMN[field]

    if field == "year":
        if not raw.isdigit() or not (1900 <= int(raw) <= 2100):
            await message.answer(t("add_movie_year_invalid", lang))
            return
        value: object = int(raw)
    elif field == "genre":
        value = raw[:100] or None
    else:  # title
        if not raw:
            await message.answer(t("edit_ask_new_value", lang))
            return
        value = raw[:255]

    service = MovieService(session)
    await service.update_fields(movie_id, **{column: value})
    await state.clear()
    await message.answer(t("edit_saved", lang), reply_markup=admin_menu_keyboard(lang))
