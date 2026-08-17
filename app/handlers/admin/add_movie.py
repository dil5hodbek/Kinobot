"""Admin: kino qo'shish FSM oqimi."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import MessageOriginType
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.keyboards.inline import add_movie_confirm_keyboard, skip_keyboard
from app.keyboards.reply import admin_menu_keyboard
from app.services.movie_service import MovieService
from app.states.admin_states import AddMovie
from app.utils.filters import ButtonText, IsAdmin
from app.utils.i18n import t

router = Router(name="admin_add_movie")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

_MAX_CODE_LEN = 20


@router.message(StateFilter(None), ButtonText("btn_add_movie"))
async def start_add(message: Message, lang: str, state: FSMContext) -> None:
    await state.set_state(AddMovie.waiting_forward)
    await message.answer(t("add_movie_forward", lang))


@router.message(AddMovie.waiting_forward)
async def got_forward(message: Message, lang: str, state: FSMContext) -> None:
    origin = message.forward_origin
    if origin is None or origin.type != MessageOriginType.CHANNEL:
        await message.answer(t("add_movie_not_forward", lang))
        return

    # channel_intake.py'ning avtomatik yo'li faqat STORAGE_CHANNEL_ID dan
    # kelgan postni qabul qiladi (xavfsizlik izohi shu faylда) — qo'lda
    # forward oqimida ham xuddi shu tekshiruv bo'lishi kerak, aks holda
    # admin bot a'zo bo'lmagan/huquqi yo'q kanaldan forward qilib kino
    # saqlashi mumkin — bu birinchi haydovchi so'raganда aniqlanardi
    # (deliver() uni faolsizlantiradi), ammo admin darhol bilmasdi.
    if origin.chat.id != settings.storage_channel_id:
        await message.answer(t("add_movie_wrong_channel", lang))
        return

    await state.update_data(
        channel_id=origin.chat.id,
        message_id=origin.message_id,
    )
    await state.set_state(AddMovie.waiting_code)
    await message.answer(t("add_movie_ask_code", lang))


@router.message(AddMovie.waiting_code)
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
    await state.set_state(AddMovie.waiting_title_uz)
    await message.answer(t("add_movie_ask_title_uz", lang))


@router.message(AddMovie.waiting_title_uz)
async def got_title_uz(message: Message, lang: str, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer(t("add_movie_ask_title_uz", lang))
        return
    await state.update_data(title_uz=title[:255])
    await state.set_state(AddMovie.waiting_title_ru)
    await message.answer(t("add_movie_ask_title_ru", lang), reply_markup=skip_keyboard(lang))


@router.message(AddMovie.waiting_title_ru)
async def got_title_ru(message: Message, lang: str, state: FSMContext) -> None:
    await state.update_data(title_ru=(message.text or "").strip()[:255] or None)
    await state.set_state(AddMovie.waiting_title_en)
    await message.answer(t("add_movie_ask_title_en", lang), reply_markup=skip_keyboard(lang))


@router.message(AddMovie.waiting_title_en)
async def got_title_en(message: Message, lang: str, state: FSMContext) -> None:
    await state.update_data(title_en=(message.text or "").strip()[:255] or None)
    await state.set_state(AddMovie.waiting_year)
    await message.answer(t("add_movie_ask_year", lang), reply_markup=skip_keyboard(lang))


@router.message(AddMovie.waiting_year)
async def got_year(message: Message, lang: str, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    year: int | None = None
    if raw:
        if not raw.isdigit() or not (1900 <= int(raw) <= 2100):
            await message.answer(t("add_movie_year_invalid", lang))
            return
        year = int(raw)
    await state.update_data(year=year)
    await state.set_state(AddMovie.waiting_genre)
    await message.answer(t("add_movie_ask_genre", lang), reply_markup=skip_keyboard(lang))


@router.message(AddMovie.waiting_genre)
async def got_genre(message: Message, lang: str, state: FSMContext) -> None:
    await state.update_data(genre=(message.text or "").strip()[:100] or None)
    await _show_confirm(message, lang, state)


@router.callback_query(StateFilter(AddMovie), F.data == "fsm_skip")
async def skip_field(callback: CallbackQuery, lang: str, state: FSMContext) -> None:
    # StateFilter(AddMovie) — shu guruhning ISTALGAN holatiga mos keladi.
    # SHART: add_link_movie.py ham "fsm_skip" ishlatadi — bu cheklov
    # bo'lmasa, qaysi router birinchi ro'yxatdan o'tgan bo'lsa o'sha HAR
    # IKKI oqim uchun callback'ni "yutib" olardi (holat mos kelmasa ham),
    # ikkinchi oqimda "O'tkazib yuborish" tugmasi jim ishlamay qolardi.
    await callback.answer()
    current = await state.get_state()
    message = callback.message
    if message is None:
        return

    if current == AddMovie.waiting_title_ru.state:
        await state.update_data(title_ru=None)
        await state.set_state(AddMovie.waiting_title_en)
        await message.answer(t("add_movie_ask_title_en", lang), reply_markup=skip_keyboard(lang))
    elif current == AddMovie.waiting_title_en.state:
        await state.update_data(title_en=None)
        await state.set_state(AddMovie.waiting_year)
        await message.answer(t("add_movie_ask_year", lang), reply_markup=skip_keyboard(lang))
    elif current == AddMovie.waiting_year.state:
        await state.update_data(year=None)
        await state.set_state(AddMovie.waiting_genre)
        await message.answer(t("add_movie_ask_genre", lang), reply_markup=skip_keyboard(lang))
    elif current == AddMovie.waiting_genre.state:
        await state.update_data(genre=None)
        await _show_confirm(message, lang, state)


async def _show_confirm(message: Message, lang: str, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(AddMovie.waiting_confirm)
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
        reply_markup=add_movie_confirm_keyboard(lang),
    )


@router.callback_query(AddMovie.waiting_confirm, F.data == "movie_save")
async def save_movie(
    callback: CallbackQuery, lang: str, state: FSMContext, session: AsyncSession
) -> None:
    await callback.answer()
    data = await state.get_data()
    service = MovieService(session)

    try:
        movie = await service.add_movie(
            code=data["code"],
            channel_id=data["channel_id"],
            message_id=data["message_id"],
            title_uz=data["title_uz"],
            title_ru=data.get("title_ru"),
            title_en=data.get("title_en"),
            year=data.get("year"),
            genre=data.get("genre"),
        )
        await session.flush()
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


@router.callback_query(AddMovie.waiting_confirm, F.data == "movie_cancel")
async def cancel_movie(callback: CallbackQuery, lang: str, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    if callback.message is not None:
        await callback.message.answer(
            t("action_cancelled", lang), reply_markup=admin_menu_keyboard(lang)
        )
