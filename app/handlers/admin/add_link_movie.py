"""Admin: LINK orqali kino qo'shish FSM oqimi.

add_movie.py bilan bir xil oqim — faqat 1-qadam "kanaldan forward" o'rniga
"URL yuborish". Qolgan qadamlar (kod/nom/yil/janr/tasdiqlash) bir xil
locale kalitlarini ishlatadi (matn manba turidan qat'i nazar bir xil).
Yuborishda video copy_message EMAS — inline havola tugmasi (movie_service.py).
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.inline import add_link_movie_confirm_keyboard, skip_keyboard
from app.keyboards.reply import admin_menu_keyboard
from app.services.audit_service import audit
from app.services.movie_service import MovieService
from app.states.admin_states import AddLinkMovie
from app.utils.filters import ButtonText, IsAdmin
from app.utils.format import looks_like_url
from app.utils.i18n import t

router = Router(name="admin_add_link_movie")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

_MAX_CODE_LEN = 20
_MAX_URL_LEN = 500


@router.message(StateFilter(None), ButtonText("btn_add_link_movie"))
async def start_add_link(message: Message, lang: str, state: FSMContext) -> None:
    await state.set_state(AddLinkMovie.waiting_url)
    await message.answer(t("add_link_ask_url", lang))


@router.message(AddLinkMovie.waiting_url)
async def got_url(message: Message, lang: str, state: FSMContext) -> None:
    url = (message.text or "").strip()
    if not url or len(url) > _MAX_URL_LEN or not looks_like_url(url):
        await message.answer(t("add_link_url_invalid", lang))
        return

    await state.update_data(external_url=url)
    await state.set_state(AddLinkMovie.waiting_code)
    await message.answer(t("add_movie_ask_code", lang))


@router.message(AddLinkMovie.waiting_code)
async def got_code(
    message: Message, lang: str, state: FSMContext, session: AsyncSession
) -> None:
    raw = (message.text or "").strip()
    service = MovieService(session)

    if raw.lower() == "auto":
        code = await service.next_auto_code()
    else:
        code = raw
        if not code or len(code) > _MAX_CODE_LEN:
            await message.answer(t("add_movie_code_invalid", lang))
            return
        if await service.code_exists(code):
            await message.answer(t("add_movie_code_exists", lang))
            return

    await state.update_data(code=code)
    await state.set_state(AddLinkMovie.waiting_title_uz)
    await message.answer(t("add_movie_ask_title_uz", lang))


@router.message(AddLinkMovie.waiting_title_uz)
async def got_title_uz(message: Message, lang: str, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer(t("add_movie_ask_title_uz", lang))
        return
    await state.update_data(title_uz=title[:255])
    await state.set_state(AddLinkMovie.waiting_title_ru)
    await message.answer(t("add_movie_ask_title_ru", lang), reply_markup=skip_keyboard(lang))


@router.message(AddLinkMovie.waiting_title_ru)
async def got_title_ru(message: Message, lang: str, state: FSMContext) -> None:
    await state.update_data(title_ru=(message.text or "").strip()[:255] or None)
    await state.set_state(AddLinkMovie.waiting_title_en)
    await message.answer(t("add_movie_ask_title_en", lang), reply_markup=skip_keyboard(lang))


@router.message(AddLinkMovie.waiting_title_en)
async def got_title_en(message: Message, lang: str, state: FSMContext) -> None:
    await state.update_data(title_en=(message.text or "").strip()[:255] or None)
    await state.set_state(AddLinkMovie.waiting_year)
    await message.answer(t("add_movie_ask_year", lang), reply_markup=skip_keyboard(lang))


@router.message(AddLinkMovie.waiting_year)
async def got_year(message: Message, lang: str, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    year: int | None = None
    if raw:
        if not raw.isdigit() or not (1900 <= int(raw) <= 2100):
            await message.answer(t("add_movie_year_invalid", lang))
            return
        year = int(raw)
    await state.update_data(year=year)
    await state.set_state(AddLinkMovie.waiting_genre)
    await message.answer(t("add_movie_ask_genre", lang), reply_markup=skip_keyboard(lang))


@router.message(AddLinkMovie.waiting_genre)
async def got_genre(message: Message, lang: str, state: FSMContext) -> None:
    await state.update_data(genre=(message.text or "").strip()[:100] or None)
    await _show_confirm(message, lang, state)


@router.callback_query(StateFilter(AddLinkMovie), F.data == "fsm_skip")
async def skip_field(callback: CallbackQuery, lang: str, state: FSMContext) -> None:
    # StateFilter(AddLinkMovie) — add_movie.py bilan bir xil "fsm_skip"
    # callback nomini ishlatamiz; cheklov bo'lmasa qaysi router birinchi
    # ro'yxatdan o'tgan bo'lsa o'sha ikkalasini ham "yutib" olardi.
    await callback.answer()
    current = await state.get_state()
    message = callback.message
    if message is None:
        return

    if current == AddLinkMovie.waiting_title_ru.state:
        await state.update_data(title_ru=None)
        await state.set_state(AddLinkMovie.waiting_title_en)
        await message.answer(t("add_movie_ask_title_en", lang), reply_markup=skip_keyboard(lang))
    elif current == AddLinkMovie.waiting_title_en.state:
        await state.update_data(title_en=None)
        await state.set_state(AddLinkMovie.waiting_year)
        await message.answer(t("add_movie_ask_year", lang), reply_markup=skip_keyboard(lang))
    elif current == AddLinkMovie.waiting_year.state:
        await state.update_data(year=None)
        await state.set_state(AddLinkMovie.waiting_genre)
        await message.answer(t("add_movie_ask_genre", lang), reply_markup=skip_keyboard(lang))
    elif current == AddLinkMovie.waiting_genre.state:
        await state.update_data(genre=None)
        await _show_confirm(message, lang, state)


async def _show_confirm(message: Message, lang: str, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(AddLinkMovie.waiting_confirm)
    dash = "—"
    await message.answer(
        t(
            "add_movie_confirm",
            lang,
            title_uz=data.get("title_uz", dash),
            title_ru=data.get("title_ru") or dash,
            title_en=data.get("title_en") or dash,
            year=data.get("year") or dash,
            genre=data.get("genre") or dash,
            code=data.get("code", dash),
        ),
        reply_markup=add_link_movie_confirm_keyboard(lang),
    )


@router.callback_query(AddLinkMovie.waiting_confirm, F.data == "link_movie_save")
async def save_link_movie(
    callback: CallbackQuery, lang: str, state: FSMContext, session: AsyncSession
) -> None:
    await callback.answer()
    data = await state.get_data()
    service = MovieService(session)

    try:
        movie = await service.add_link_movie(
            code=data["code"],
            external_url=data["external_url"],
            title_uz=data["title_uz"],
            title_ru=data.get("title_ru"),
            title_en=data.get("title_en"),
            year=data.get("year"),
            genre=data.get("genre"),
        )
        await session.flush()
        await audit(
            session,
            admin_id=callback.from_user.id,
            action="add_link_movie",
            entity_type="movie",
            entity_id=movie.id,
            metadata=movie.code,
        )
    except (IntegrityError, KeyError):
        await session.rollback()
        await state.clear()
        if callback.message is not None:
            await callback.message.answer(
                t("add_movie_error", lang), reply_markup=admin_menu_keyboard(lang)
            )
        return

    await state.clear()
    if callback.message is not None:
        await callback.message.answer(
            t("add_movie_saved", lang, code=movie.code),
            reply_markup=admin_menu_keyboard(lang),
        )


@router.callback_query(AddLinkMovie.waiting_confirm, F.data == "link_movie_cancel")
async def cancel_link_movie(callback: CallbackQuery, lang: str, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    if callback.message is not None:
        await callback.message.answer(
            t("action_cancelled", lang), reply_markup=admin_menu_keyboard(lang)
        )
